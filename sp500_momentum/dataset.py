"""Data download steps. Run in this order:

uv run python -m sp500_momentum.dataset membership   # Wikipedia: current list + changes
uv run python -m sp500_momentum.dataset coverage     # which removed members yfinance lacks
uv run python -m sp500_momentum.dataset av-pull      # Alpha Vantage, ~23 tickers a day; rerun daily
uv run python -m sp500_momentum.dataset av-status    # progress of the pull
"""

import time

from loguru import logger
import pandas as pd
import typer

from sp500_momentum.config import (
    AV_DAILY_BUDGET,
    AV_MANIFEST,
    AV_MONTHLY_DIR,
    AV_SLEEP_SECONDS,
    REMOVED_COVERAGE,
    START_DATE,
    WIKIPEDIA_DIR,
)
from sp500_momentum.sources import alphavantage as av
from sp500_momentum.sources import wikipedia, yahoo

app = typer.Typer(help="Download raw data for the project.")


def _read_manifest() -> pd.DataFrame:
    if AV_MANIFEST.exists():
        return pd.read_csv(AV_MANIFEST, parse_dates=["removed_date", "av_first", "av_last"])
    return pd.DataFrame(columns=["ticker"])


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
    removed = wikipedia.removed_since(changes, current, start)
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


@app.command("av-pull")
def av_pull(max_calls: int = AV_DAILY_BUDGET):
    """Pull monthly adjusted history from Alpha Vantage for the next tickers in the queue."""
    cov = pd.read_csv(REMOVED_COVERAGE, parse_dates=["removed_date"])
    manifest = _read_manifest()
    queue = av.build_queue(cov, manifest)
    if queue.empty:
        logger.success("Queue is empty: every missing ticker has been tried.")
        return
    logger.info(f"{len(queue)} tickers left in the queue; pulling up to {max_calls} now")
    key = av.api_key()
    AV_MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        for _, r in queue.head(max_calls).iterrows():
            df = av.fetch_monthly_adjusted(r["ticker"], key)
            status = av.validate(df, r["removed_date"])
            if df is not None:
                df.to_csv(AV_MONTHLY_DIR / f"{r['ticker']}.csv", index=False)
            rows.append(
                {
                    "ticker": r["ticker"],
                    "name": r["name"],
                    "reason_cat": r["reason_cat"],
                    "removed_date": r["removed_date"],
                    "status": status,
                    "av_months": 0 if df is None else len(df),
                    "av_first": None if df is None else df["timestamp"].min(),
                    "av_last": None if df is None else df["timestamp"].max(),
                    "fetched_at": pd.Timestamp.now().floor("s"),
                }
            )
            logger.info(f"{r['ticker']:6s} {r['reason_cat']:15s} -> {status}")
            time.sleep(AV_SLEEP_SECONDS)
    except av.QuotaExhausted as e:
        logger.warning(f"Alpha Vantage quota reached, stopping for today: {e}")
    finally:
        if rows:
            new = pd.DataFrame(rows)
            out = new if manifest.empty else pd.concat([manifest, new], ignore_index=True)
            AV_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
            out.to_csv(AV_MANIFEST, index=False)
            logger.success(f"Saved {len(new)} results to the manifest ({len(out)} total)")
    av_status()


@app.command("av-status")
def av_status():
    """Show how far the Alpha Vantage pull has got."""
    cov = pd.read_csv(REMOVED_COVERAGE, parse_dates=["removed_date"])
    manifest = _read_manifest()
    left = len(av.build_queue(cov, manifest))
    done = 0 if manifest.empty else len(manifest)
    logger.info(f"Tried {done}, left {left} (about {-(-left // AV_DAILY_BUDGET)} more days)")
    if done:
        logger.info(f"\n{manifest.groupby(['reason_cat', 'status']).size().unstack(fill_value=0)}")


if __name__ == "__main__":
    app()
