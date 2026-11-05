"""Diagnosis of what the strategies pick, and where they win or lose (#16).

Descriptive only (decisions.md, 4 Nov): nothing here chooses or tunes a strategy.

- Picks are joined back to the monthly table (next month's result) and the feature table (sector,
  VIX, exposures). Periods are set by decision date, as everywhere else.
- **Margins of error are computed across months, not picks.** Picks made in the same month move
  together, so each slice is first averaged within each month, then over months; the standard error
  is the spread of those monthly values / sqrt(months).
- Exposures are within-month percentiles among all eligible members (50 = the average member), so a
  pick's "volatility 90" means it was more volatile than 90% of that month's members.
"""

import numpy as np
import pandas as pd

from sp500_momentum.backtest import eligible

EXPOSURES = {
    "vol_12m": "Volatility (12 months)",
    "beta_36m": "Beta to SPY (36 months)",
    "log_dollar_vol": "Size (dollar volume)",
    "ret_6m": "6-month return",
    "ret_1m": "Last month's return",
}
FEATURE_COLUMNS = ["date", "ticker", "sector", "vix", *EXPOSURES]


def universe(panel: pd.DataFrame, features: pd.DataFrame, periods: dict) -> pd.DataFrame:
    """Every eligible member-month with a known next-month result, with its sector, VIX,
    within-month exposure percentiles and period (by decision date; rows outside every period
    are dropped). `periods`: {name: (start, end)} decision windows [start, end)."""
    rows = panel[eligible(panel) & panel["is_beat_spy_1m"].notna()]
    rows = rows[
        [
            "date",
            "ticker",
            "price_ticker",
            "fwd_excess_1m",
            "is_beat_spy_1m",
            "fwd_trunc_1m",
            "spy_fwd_ret_1m",
        ]
    ]
    rows = rows.merge(features[FEATURE_COLUMNS], on=["date", "ticker"], how="left")
    for col in EXPOSURES:
        rows[f"{col}_pct"] = rows.groupby("date")[col].rank(pct=True) * 100
    rows["month"] = pd.PeriodIndex(rows["date"], freq="M")
    rows["period"] = pd.NA
    for name, (start, end) in periods.items():
        keep = rows["month"] >= pd.Period(start, freq="M")
        if end:
            keep &= rows["month"] < pd.Period(end, freq="M")
        rows.loc[keep, "period"] = name
    rows["beat"] = rows["is_beat_spy_1m"].astype(float)
    rows["left_within_12m"] = left_index(panel, rows)
    rows["delisted_next_month"] = rows["fwd_trunc_1m"].eq(True)
    return rows.dropna(subset=["period"]).reset_index(drop=True)


def mark_picks(rows: pd.DataFrame, picks: dict[pd.Period, list[str]], name: str) -> pd.DataFrame:
    """Add a 0/1 column `name`: the strategy picked this member at this decision."""
    chosen = {(m, t) for m, names in picks.items() for t in names}
    out = rows.copy()
    out[name] = [int((m, t) in chosen) for m, t in zip(out["month"], out["price_ticker"])]
    return out


def regimes(rows: pd.DataFrame, invested: pd.Series, vix_cut: float) -> pd.DataFrame:
    """Add three regime labels per decision month: SPY vs its trend (from the #15 signal), VIX
    high or low against a cut fixed in advance, and whether SPY rose the next month (what the
    market did, known only afterwards: a description, not a signal)."""
    out = rows.copy()
    on = out["month"].map(invested)
    out["trend"] = np.where(
        on.astype("boolean").fillna(True), "SPY above its trend", "SPY below its trend"
    )
    vix = out.groupby("month")["vix"].transform("first")
    out["vix_level"] = np.where(vix > vix_cut, "VIX high", "VIX low")
    out["market"] = np.where(out["spy_fwd_ret_1m"] > 0, "SPY up next month", "SPY down next month")
    return out


def _monthly(rows: pd.DataFrame, by: list[str], value: str) -> pd.DataFrame:
    return rows.groupby([*by, "month"])[value].mean().rename(value).reset_index()


def slice_table(rows: pd.DataFrame, pick: str, by: str) -> pd.DataFrame:
    """Per period and slice: months, picks, the picks' hit rate and average excess return (both
    with month-level standard errors), and the base rate of all members in the same slice and
    months. A slice only counts months in which the strategy picked something in it."""
    keys = ["period", by]
    picked = rows[rows[pick] == 1]
    hit = _monthly(picked, keys, "beat")
    ex = _monthly(picked, keys, "fwd_excess_1m")
    base = _monthly(rows, keys, "beat").rename(columns={"beat": "base"})
    m = hit.merge(ex, on=[*keys, "month"]).merge(base, on=[*keys, "month"], how="left")
    g = m.groupby(keys)
    out = pd.DataFrame(
        {
            "months": g.size(),
            "picks": picked.groupby(keys).size(),
            "hit_rate": g["beat"].mean(),
            "hit_se": g["beat"].std(ddof=1) / np.sqrt(g.size()),
            "base_rate": g["base"].mean(),
            "excess": g["fwd_excess_1m"].mean(),
            "excess_se": g["fwd_excess_1m"].std(ddof=1) / np.sqrt(g.size()),
        }
    )
    out["lift"] = out["hit_rate"] - out["base_rate"]
    return out


def exposures(rows: pd.DataFrame, picks: list[str]) -> pd.DataFrame:
    """The average within-month percentile of each exposure among each strategy's picks, by
    period (50 = the average member)."""
    cols = [f"{c}_pct" for c in EXPOSURES]
    out = {
        (p, s): rows[(rows["period"] == p) & (rows[s] == 1)][cols].mean()
        for s in picks
        for p in rows["period"].unique()
    }
    table = pd.DataFrame(out).T
    table.columns = list(EXPOSURES.values())
    table.index.names = ["period", "strategy"]
    return table


def sector_mix(rows: pd.DataFrame, picks: list[str]) -> pd.DataFrame:
    """Share of each strategy's picks in each sector next to the members' share, by period."""
    parts = {"members": rows.groupby("period")["sector"].value_counts(normalize=True)}
    for s in picks:
        parts[s] = rows[rows[s] == 1].groupby("period")["sector"].value_counts(normalize=True)
    return pd.DataFrame(parts).fillna(0.0)


def left_index(panel: pd.DataFrame, rows: pd.DataFrame, within: int = 12) -> pd.Series:
    """For each row: was the member gone from the index within `within` months after the decision
    (and before the panel's last month)?"""
    months = pd.PeriodIndex(panel["date"], freq="M")
    last_seen = pd.Series(months, index=panel.index).groupby(panel["ticker"]).max()
    end = months.max()
    seen = rows["ticker"].map(last_seen)
    horizon = rows["month"] + within
    return (seen < horizon) & (horizon <= end)


def worst_picks(rows: pd.DataFrame, pick: str, n: int = 8) -> pd.DataFrame:
    """The n picks with the worst next-month return against SPY, per period."""
    cols = [
        "period",
        "date",
        "ticker",
        "sector",
        "fwd_excess_1m",
        "ret_6m",
        "vol_12m_pct",
        "delisted_next_month",
        "left_within_12m",
    ]
    picked = rows[rows[pick] == 1]
    worst = picked.sort_values("fwd_excess_1m").groupby("period", sort=False).head(n)
    return worst[cols].sort_values(["period", "fwd_excess_1m"]).reset_index(drop=True)
