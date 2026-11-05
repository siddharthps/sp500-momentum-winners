"""Data download steps. Run in this order:

uv run python -m sp500_momentum.dataset membership   # Wikipedia: current list + changes
uv run python -m sp500_momentum.dataset coverage     # which removed members yfinance lacks
uv run python -m sp500_momentum.dataset yahoo-daily  # yfinance daily prices + benchmarks
uv run python -m sp500_momentum.dataset fred         # FRED macro series
uv run python -m sp500_momentum.dataset av-pull      # Alpha Vantage, ~23 tickers a day; rerun daily
uv run python -m sp500_momentum.dataset av-status    # progress of the pull
"""

import time

from loguru import logger
import pandas as pd
import typer

from sp500_momentum import notify
from sp500_momentum.config import (
    AV_DAILY_BUDGET,
    AV_MANIFEST,
    AV_MONTHLY_DIR,
    AV_SLEEP_SECONDS,
    BENCHMARKS,
    FRED_DIR,
    FRED_SERIES,
    FRED_START,
    PRICE_START,
    REASON_OVERRIDES,
    REMOVED_COVERAGE,
    START_DATE,
    WIKIPEDIA_DIR,
    YAHOO_DAILY_DIR,
    YAHOO_MANIFEST,
    YAHOO_SUSPECT,
)
from sp500_momentum.sources import alphavantage as av
from sp500_momentum.sources import fred as fred_src
from sp500_momentum.sources import wikipedia, yahoo

app = typer.Typer(help="Download raw data for the project.")


def _read_manifest() -> pd.DataFrame:
    if AV_MANIFEST.exists():
        return pd.read_csv(AV_MANIFEST, parse_dates=["removed_date", "av_first", "av_last"])
    return pd.DataFrame(columns=["ticker"])


def _coverage_for_av() -> pd.DataFrame:
    """Coverage table, with yfinance series that failed the monthly build's liquidity check
    (another security reused the ticker, e.g. CPWR, EP) treated as missing."""
    cov = pd.read_csv(REMOVED_COVERAGE, parse_dates=["removed_date"])
    if YAHOO_SUSPECT.exists():
        bad = set(pd.read_csv(YAHOO_SUSPECT)["ticker"])
        cov.loc[cov["ticker"].isin(bad), "yahoo_ok"] = False
    return cov


@app.command()
def membership():
    """Save today's S&P 500 list and the historical changes table from Wikipedia."""
    WIKIPEDIA_DIR.mkdir(parents=True, exist_ok=True)
    current = wikipedia.fetch_current()
    changes = wikipedia.fetch_changes()
    current.to_csv(WIKIPEDIA_DIR / "sp500_current.csv", index=False)
    changes.to_csv(WIKIPEDIA_DIR / "sp500_changes.csv", index=False)
    logger.success(
        f"{len(current)} current members; {len(changes)} changes "
        f"({changes['date'].min():%Y-%m-%d} to {changes['date'].max():%Y-%m-%d})"
    )


@app.command()
def coverage(start: str = START_DATE):
    """For every member removed since `start`, check whether yfinance has its history."""
    current = pd.read_csv(WIKIPEDIA_DIR / "sp500_current.csv")
    changes = pd.read_csv(WIKIPEDIA_DIR / "sp500_changes.csv", parse_dates=["date"])
    for col in ["added_ticker", "removed_ticker"]:  # older scrapes kept stray chars ("JCP |")
        changes[col] = changes[col].where(
            changes[col].isna(), changes[col].map(wikipedia.normalize_ticker)
        )
    removed = wikipedia.removed_since(changes, current, start)
    for t, cat in REASON_OVERRIDES.items():
        removed.loc[removed["ticker"] == t, "reason_cat"] = cat
    logger.info(
        f"{len(removed)} tickers removed since {start} and not members today; checking yfinance"
    )
    span = yahoo.history_span(removed["ticker"].tolist())
    cov = removed.merge(span, on="ticker", how="left")
    cov["yahoo_ok"] = yahoo.yahoo_usable(cov, cov["removed_date"])
    REMOVED_COVERAGE.parent.mkdir(parents=True, exist_ok=True)
    cov.to_csv(REMOVED_COVERAGE, index=False)
    table = pd.crosstab(
        cov["reason_cat"],
        cov["yahoo_ok"].map({True: "yfinance_ok", False: "missing"}),
        margins=True,
    )
    logger.success(f"Saved {REMOVED_COVERAGE.name}\n{table}")


@app.command("yahoo-daily")
def yahoo_daily(
    start: str = PRICE_START,
    refresh: bool = typer.Option(False, help="Download every ticker again, not just new ones"),
    active_only: bool = typer.Option(
        False,
        help="Download today's members and the benchmarks again (full history); keep removed",
    ),
):
    """Daily prices from yfinance: current members, removed members it covers, benchmarks.

    Saves one parquet file per ticker in data/raw/yahoo/daily/ and a manifest. Data ends at
    yesterday's close (today's bar may be half-finished). Without --refresh, tickers that
    already have a file are skipped, so a failed run can simply be rerun.

    `--active-only` is the monthly update. Each active ticker's whole history is downloaded
    again, never appended: the adjusted close is recomputed backwards after every dividend or
    split, so new days appended to an old file would mix two adjustment bases. Removed members'
    files never change, so they're left as they are.
    """
    current = pd.read_csv(WIKIPEDIA_DIR / "sp500_current.csv")
    cov = pd.read_csv(REMOVED_COVERAGE, parse_dates=["removed_date"])
    universe = yahoo.price_universe(current, cov, BENCHMARKS)
    YAHOO_DAILY_DIR.mkdir(parents=True, exist_ok=True)

    todo = universe
    if active_only:
        todo = universe[universe["group"] != "removed"]
    elif not refresh:
        have = {p.name for p in YAHOO_DAILY_DIR.glob("*.parquet")}
        todo = universe[~universe["ticker"].map(yahoo.file_name).isin(have)]
    end = pd.Timestamp.now().strftime("%Y-%m-%d")
    logger.info(
        f"{len(universe)} tickers in the universe "
        f"({universe['group'].value_counts().to_dict()}); downloading {len(todo)} "
        f"from {start} to {end} (exclusive)"
    )

    frames = yahoo.download_daily(todo["ticker"].tolist(), start=start, end=end)
    # yfinance sometimes drops a ticker inside a big batch; try those once more on their own.
    retry = [t for t, df in frames.items() if df.empty]
    if retry:
        logger.info(f"Retrying {len(retry)} empty tickers one batch at a time: {retry[:10]}...")
        frames.update(yahoo.download_daily(retry, start=start, end=end, chunk=10))

    for t, df in frames.items():
        if not df.empty:
            df.to_parquet(YAHOO_DAILY_DIR / yahoo.file_name(t), index=False)

    # Rebuild the manifest from the files on disk, so it always matches them.
    rows = []
    for _, r in universe.iterrows():
        path = YAHOO_DAILY_DIR / yahoo.file_name(r["ticker"])
        df = pd.read_parquet(path) if path.exists() else None
        rows.append(
            {
                "ticker": r["ticker"],
                "group": r["group"],
                "removed_date": r["removed_date"],
                "status": yahoo.check_daily(df, r["removed_date"]),
                "rows": 0 if df is None else len(df),
                "first": None if df is None else df["date"].min(),
                "last": None if df is None else df["date"].max(),
                "n_dividends": 0 if df is None else int((df["dividends"] > 0).sum()),
                "n_splits": 0 if df is None else int((df["stock_splits"] > 0).sum()),
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(YAHOO_MANIFEST, index=False)
    table = pd.crosstab(manifest["group"], manifest["status"], margins=True)
    logger.success(f"Saved {YAHOO_MANIFEST.name}: {manifest['rows'].sum():,} daily rows\n{table}")


@app.command()
def fred(start: str = FRED_START):
    """Download the FRED macro series in FRED_SERIES (full refresh: 6 small requests)."""
    FRED_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for sid, meta in FRED_SERIES.items():
        df = fred_src.fetch_series(sid, start)
        df.to_csv(FRED_DIR / f"{sid}.csv", index=False)
        rows.append(
            {
                "series": sid,
                "name": meta["name"],
                "rows": len(df),
                "first": df["date"].min().date(),
                "last": df["date"].max().date(),
                "last_value": df["value"].iloc[-1],
            }
        )
    table = pd.DataFrame(rows).to_string(index=False)
    logger.success(f"Saved {len(rows)} FRED series to {FRED_DIR}\n{table}")


@app.command("av-pull")
def av_pull(max_calls: int = AV_DAILY_BUDGET):
    """Pull monthly adjusted history from Alpha Vantage for the next tickers in the queue."""
    cov = _coverage_for_av()
    manifest = _read_manifest()
    queue = av.build_queue(cov, manifest)
    # Files saved by a run that was killed before recording them: add them without a call.
    recovered = av.recover_from_disk(queue, AV_MONTHLY_DIR)
    if recovered:
        manifest = _append_manifest(manifest, recovered)
        logger.success(
            f"Recovered {len(recovered)} files already on disk into the manifest: "
            f"{', '.join(r['ticker'] for r in recovered)}"
        )
        queue = av.build_queue(cov, manifest)
    if queue.empty:
        logger.success("Queue is empty: every missing ticker has been tried.")
        if max_calls > 0:  # the scheduled run, not a manual check
            notify.private(notify.av_message({}, 0, len(recovered), False))
        return
    logger.info(f"{len(queue)} tickers left in the queue; pulling up to {max_calls} now")
    if max_calls <= 0:
        av_status()
        return
    key = av.api_key()
    AV_MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    tonight: dict[str, int] = {}
    quota_hit = False
    try:
        for _, r in queue.head(max_calls).iterrows():
            df = av.fetch_monthly_adjusted(r["ticker"], key)
            if df is not None:
                df.to_csv(AV_MONTHLY_DIR / f"{r['ticker']}.csv", index=False)
            row = av.manifest_row(r, df, pd.Timestamp.now())
            # Recorded straight away, so a killed run loses at most the call in flight.
            manifest = _append_manifest(manifest, [row])
            tonight[row["status"]] = tonight.get(row["status"], 0) + 1
            logger.info(f"{r['ticker']:6s} {r['reason_cat']:15s} -> {row['status']}")
            time.sleep(AV_SLEEP_SECONDS)
    except av.QuotaExhausted as e:
        # Alpha Vantage's quota message quotes the API key; don't write it to the log.
        msg = str(e).replace(key, "***")
        logger.warning(f"Alpha Vantage quota reached, stopping for today: {msg}")
        quota_hit = True
    av_status()
    left = len(av.build_queue(cov, manifest))
    notify.private(notify.av_message(tonight, left, len(recovered), quota_hit))


def _append_manifest(manifest: pd.DataFrame, rows: list[dict]) -> pd.DataFrame:
    """Add rows to the manifest and write it to disk at once."""
    new = pd.DataFrame(rows)
    out = new if manifest.empty else pd.concat([manifest, new], ignore_index=True)
    AV_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(AV_MANIFEST, index=False)
    return out


@app.command("av-status")
def av_status():
    """Show how far the Alpha Vantage pull has got."""
    cov = _coverage_for_av()
    manifest = _read_manifest()
    left = len(av.build_queue(cov, manifest))
    done = 0 if manifest.empty else len(manifest)
    logger.info(f"Tried {done}, left {left} (about {-(-left // AV_DAILY_BUDGET)} more days)")
    if done:
        logger.info(f"\n{manifest.groupby(['reason_cat', 'status']).size().unstack(fill_value=0)}")


if __name__ == "__main__":
    app()
