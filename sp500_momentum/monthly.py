"""The monthly table: one row per S&P 500 member per month-end, with prices and returns.

    uv run python -m sp500_momentum.monthly build

Inputs: Wikipedia membership, yfinance daily files, Alpha Vantage monthly files. Rerun it
whenever more Alpha Vantage data arrives; it rebuilds everything from the raw files.

Prices per stock and month:
- `close_adj`: adjusted close on the last trading day of the month (what features use).
- `entry_px`: the price we can trade at after the decision. For yfinance, the adjusted open of
  the next trading day (open * adj_close / close). Alpha Vantage is monthly only, so there it's
  the month-end adjusted close.

Targets, for each hold X in HOLD_MONTHS:
- `fwd_ret_Xm` = entry_px X months later / entry_px now - 1.
- Delisted (Alpha Vantage) names keep prices up to the month that contains their removal date,
  then stop. If a stock's prices end during the hold, the position is valued at its last price
  and held as cash (0%) for the rest, flagged in `fwd_trunc_Xm`.
- `fwd_excess_Xm` subtracts SPY's return over the same window; `is_beat_spy_Xm` = excess > 0;
  `is_top_decile_Xm` = in the top 10% of that month's members.
"""

from loguru import logger
import numpy as np
import pandas as pd
import typer

from sp500_momentum.config import (
    AV_MANIFEST,
    AV_MONTHLY_DIR,
    HOLD_MONTHS,
    MIN_MEMBER_DOLLAR_VOLUME,
    MISSING_ADDS,
    MONTHLY_COVERAGE,
    MONTHLY_PANEL,
    PRICE_FLAGS,
    RENAMES,
    START_DATE,
    WIKIPEDIA_DIR,
    YAHOO_DAILY_DIR,
    YAHOO_SUSPECT,
)
from sp500_momentum.membership import month_ends, point_in_time, repair_changes

app = typer.Typer(help="Build the monthly member table.")


@app.callback()
def _main():
    """Build the monthly member table."""


PAST = {
    "ret_1m": (0, 1),
    "ret_3m": (0, 3),
    "ret_6m": (0, 6),
    "ret_12m": (0, 12),
    "ret_12_1m": (1, 12),
}


def yahoo_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Daily yfinance rows -> month, close_adj, entry_px (next trading day's adjusted open),
    dollar_vol (median daily close * volume in the month, for the liquidity check)."""
    d = daily.sort_values("date").copy()
    d["open_adj"] = d["open"] * d["adj_close"] / d["close"]
    d["dv"] = d["close"] * d["volume"]
    d["month"] = d["date"].dt.to_period("M")
    g = d.groupby("month").agg(
        close_adj=("adj_close", "last"),
        first_open=("open_adj", "first"),
        dollar_vol=("dv", "median"),
    )
    g = g.reindex(pd.period_range(g.index.min(), g.index.max(), freq="M"))
    g["entry_px"] = g["first_open"].shift(-1)
    g.index.name = "month"
    return g[["close_adj", "entry_px", "dollar_vol"]].reset_index()


def av_monthly(av: pd.DataFrame, removed_date) -> pd.DataFrame:
    """Alpha Vantage monthly rows -> month, close_adj, entry_px, cut after the removal month."""
    a = av.sort_values("timestamp").copy()
    a["month"] = pd.to_datetime(a["timestamp"]).dt.to_period("M")
    a = a[a["month"] <= pd.Timestamp(removed_date).to_period("M")]
    a = a.groupby("month").agg(close_adj=("adjusted close", "last"))
    a = a.reindex(pd.period_range(a.index.min(), a.index.max(), freq="M"))
    a["entry_px"] = a["close_adj"]
    a.index.name = "month"
    return a.reset_index()


def add_returns(p: pd.DataFrame, holds: list[int], data_end: pd.Period) -> pd.DataFrame:
    """Past and forward returns for one stock's contiguous monthly prices.

    `data_end` is the last month whose entry price is known for the market as a whole.
    """
    p = p.sort_values("month").reset_index(drop=True)
    c = p["close_adj"]
    for name, (skip, back) in PAST.items():
        p[name] = c.shift(skip) / c.shift(back) - 1
    last = p.loc[p["close_adj"].notna(), "month"].max()
    last_val = p.loc[p["month"] == last, "close_adj"].iloc[0]
    px = p["entry_px"]
    for x in holds:
        exit_m = p["month"] + x
        normal = px.shift(-x) / px - 1
        trunc = (exit_m > last) & (p["month"] <= last)
        fwd = normal.where(~trunc, last_val / px - 1)
        p[f"fwd_ret_{x}m"] = fwd.where(exit_m <= data_end)
        p[f"fwd_trunc_{x}m"] = trunc & (exit_m <= data_end)
    return p


def load_prices() -> pd.DataFrame:
    """All monthly price series: yfinance files plus Alpha Vantage files with status ok."""
    parts = []
    for path in YAHOO_DAILY_DIR.glob("*.parquet"):
        m = yahoo_monthly(pd.read_parquet(path))
        m["price_ticker"] = path.stem.replace("_", "^")
        m["source"] = "yahoo"
        parts.append(m)
    if AV_MANIFEST.exists():
        man = pd.read_csv(AV_MANIFEST, parse_dates=["removed_date"])
        for _, r in man[man["status"] == "ok"].iterrows():
            av = pd.read_csv(AV_MONTHLY_DIR / f"{r['ticker']}.csv", parse_dates=["timestamp"])
            m = av_monthly(av, r["removed_date"])
            m["price_ticker"] = r["ticker"]
            m["source"] = "alphavantage"
            parts.append(m)
    return pd.concat(parts, ignore_index=True)


def suspect_tickers(
    members: pd.DataFrame, prices: pd.DataFrame, min_dollar_vol: float
) -> pd.Series:
    """yfinance tickers whose median daily dollar volume over their member months is too low
    for an S&P 500 stock: the data belongs to another security that reused the ticker."""
    y = prices[prices["source"] == "yahoo"][["price_ticker", "month", "dollar_vol"]]
    m = members.assign(month=members["date"].dt.to_period("M"))
    j = m.merge(y, left_on=["ticker", "month"], right_on=["price_ticker", "month"])
    med = j.groupby("ticker")["dollar_vol"].median()
    return med[med.fillna(0) < min_dollar_vol]


def build_panel(
    members: pd.DataFrame, prices: pd.DataFrame, holds: list[int], drop: set[str] = frozenset()
) -> pd.DataFrame:
    """Join membership to returns and add SPY-relative targets.

    Tickers in `drop` get no prices (their yfinance data is another security)."""
    spy = prices[prices["price_ticker"] == "SPY"]
    data_end = spy.loc[spy["entry_px"].notna(), "month"].max()
    rets = prices.groupby("price_ticker", group_keys=False)[prices.columns].apply(
        add_returns, holds=holds, data_end=data_end
    )
    spy_f = rets[rets["price_ticker"] == "SPY"].set_index("month")
    panel = members.copy()
    panel["month"] = panel["date"].dt.to_period("M")
    rets = rets[~rets["price_ticker"].isin(drop)]
    panel = panel.merge(
        rets, left_on=["ticker", "month"], right_on=["price_ticker", "month"], how="left"
    )
    panel["has_price"] = panel["close_adj"].notna()
    for x in holds:
        f = f"fwd_ret_{x}m"
        panel[f"spy_fwd_ret_{x}m"] = panel["month"].map(spy_f[f])
        panel[f"fwd_excess_{x}m"] = panel[f] - panel[f"spy_fwd_ret_{x}m"]
        known = panel[f].notna()
        panel[f"is_beat_spy_{x}m"] = (panel[f"fwd_excess_{x}m"] > 0).astype("Int8").where(known)
        pct = panel[known].groupby("date")[f].rank(pct=True)
        panel[f"is_top_decile_{x}m"] = (pct > 0.9).astype("Int8").reindex(panel.index)
    panel["month"] = panel["month"].astype(str)
    return panel


def price_flags(panel: pd.DataFrame) -> pd.DataFrame:
    """Member months with moves big enough to suggest a wrong ticker or bad data."""
    big = panel[(panel["ret_1m"] > 1.0) | (panel["ret_1m"] < -0.75)]
    return big[["date", "ticker", "price_ticker", "source", "ret_1m", "close_adj"]]


@app.command()
def build(start: str = START_DATE):
    """Rebuild data/processed/monthly_panel.parquet from the raw files."""
    current = pd.read_csv(WIKIPEDIA_DIR / "sp500_current.csv")
    changes = pd.read_csv(WIKIPEDIA_DIR / "sp500_changes.csv", parse_dates=["date"])
    changes = repair_changes(changes, RENAMES, MISSING_ADDS)
    spy_days = pd.read_parquet(YAHOO_DAILY_DIR / "SPY.parquet", columns=["date"])["date"]
    dates = month_ends(spy_days, start)
    members = point_in_time(current, changes, dates)
    prices = load_prices()
    suspect = suspect_tickers(members, prices, MIN_MEMBER_DOLLAR_VOLUME)
    logger.info(
        f"{len(suspect)} yfinance tickers fail the liquidity check (median member-month dollar "
        f"volume < ${MIN_MEMBER_DOLLAR_VOLUME / 1e6:.0f}M), prices dropped:\n"
        f"{(suspect / 1e6).round(2).to_string()}"
    )
    current_set = set(current["ticker"])
    pd.DataFrame({"ticker": suspect.index, "median_dollar_vol": suspect.values}).assign(
        is_current=lambda d: d["ticker"].isin(current_set)
    ).to_csv(YAHOO_SUSPECT, index=False)
    panel = build_panel(members, prices, HOLD_MONTHS, drop=set(suspect.index))

    MONTHLY_PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(MONTHLY_PANEL, index=False)

    cov = panel.groupby("date").agg(
        members=("ticker", "size"),
        priced=("has_price", "sum"),
        yahoo=("source", lambda s: (s == "yahoo").sum()),
        alphavantage=("source", lambda s: (s == "alphavantage").sum()),
    )
    cov["missing"] = cov["members"] - cov["priced"]
    cov["priced_pct"] = (cov["priced"] / cov["members"]).round(4)
    MONTHLY_COVERAGE.parent.mkdir(parents=True, exist_ok=True)
    cov.to_csv(MONTHLY_COVERAGE)
    flags = price_flags(panel)
    flags.to_csv(PRICE_FLAGS, index=False)

    missing = panel[~panel["has_price"]].groupby("ticker").size().sort_values(ascending=False)
    logger.success(
        f"{len(panel):,} rows, {panel['date'].nunique()} month-ends, "
        f"{panel['ticker'].nunique()} tickers; priced {panel['has_price'].mean():.1%} "
        f"(yahoo {np.mean(panel['source'] == 'yahoo'):.1%}, "
        f"alphavantage {np.mean(panel['source'] == 'alphavantage'):.1%})"
    )
    logger.info(
        f"Coverage by year (share of members priced):\n"
        f"{cov['priced_pct'].groupby(cov.index.year).mean().round(3).to_string()}"
    )
    logger.info(
        f"{len(missing)} tickers have unpriced member months; top 15:\n"
        f"{missing.head(15).to_string()}"
    )
    logger.info(f"{len(flags)} member months with moves > +100% or < -75% ({PRICE_FLAGS.name})")


if __name__ == "__main__":
    app()
