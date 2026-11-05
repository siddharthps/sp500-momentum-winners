"""The dashboard's calculations (#40): plain pandas, no Streamlit, tested in CI.

Deployed to the Hugging Face Space next to app.py, so it can't import the project's package (that
would install the whole model stack): the few calculations it needs live here, and the tests
check them against the package where they overlap.
"""

import numpy as np
import pandas as pd

START_DOLLARS = 10_000
# The project's validated chart palette (sp500_momentum.plots), in the same fixed order.
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a"]
INK_2 = "#52514e"
LINES = {  # column -> (label, colour)
    "model": ("Headline model, top 10", SLOTS[0]),
    "rule_6m": ("Rule: 6-month top 10", SLOTS[1]),
    "chosen_rule": ("Chosen rule (top 5, 6-month, held 6)", SLOTS[2]),
    "spy": ("SPY", INK_2),
}
STRATEGY_NAMES = {"model": "Headline model", "rule": "Rule: top 6-month return"}


def latest_picks(live_picks: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """The most recent decision date and its picks, both strategies, in rank order."""
    latest = live_picks["decision_date"].max()
    picks = live_picks[live_picks["decision_date"] == latest].sort_values(["strategy", "rank"])
    return latest, picks


def window(returns: pd.DataFrame, start: str, end: str | None = None) -> pd.DataFrame:
    """Rows of the monthly returns (column `month_earned`, 'YYYY-MM') in [start, end]."""
    m = returns["month_earned"]
    keep = m >= start
    if end:
        keep &= m <= end
    return returns[keep].set_index("month_earned")


def value_paths(returns: pd.DataFrame, start_value: float = START_DOLLARS) -> pd.DataFrame:
    """What `start_value` grows to by the end of each month, per column, with the starting point
    as the first row (one month before the first return)."""
    if returns.empty:
        return returns
    first = (pd.Period(returns.index[0], freq="M") - 1).strftime("%Y-%m")
    grown = start_value * (1 + returns).cumprod()
    start = pd.DataFrame(
        [[start_value] * returns.shape[1]], columns=returns.columns, index=[first]
    )
    return pd.concat([start, grown])


def summary(returns: pd.DataFrame) -> pd.DataFrame:
    """Per column: what $10,000 became, yearly return, volatility, worst fall, months."""
    rows = {}
    for c in returns:
        r = returns[c].dropna()
        if r.empty:
            continue
        growth = (1 + r).cumprod()
        peak = np.maximum(growth.cummax(), 1.0)
        rows[c] = {
            "$10,000 became": START_DOLLARS * growth.iloc[-1],
            "yearly return": growth.iloc[-1] ** (12 / len(r)) - 1,
            "volatility": r.std() * np.sqrt(12),
            "worst fall": float((growth / peak - 1).min()),
            "months": len(r),
        }
    return pd.DataFrame(rows).T


def live_summary(live: pd.DataFrame) -> pd.DataFrame:
    """Per strategy over all live months: months, average monthly return vs SPY, the share of
    picks that beat SPY, and the base rate (all members) over the same months."""
    if live.empty:
        return pd.DataFrame()
    g = live.assign(excess=live["ret"] - live["spy"]).groupby("strategy")
    return pd.DataFrame(
        {
            "months": g.size(),
            "average month vs SPY": g["excess"].mean(),
            "picks beating SPY": g["beat"].sum() / g["priced"].sum(),
            "base rate": g["base_rate"].mean(),
        }
    ).rename(index=STRATEGY_NAMES)


def drift_level(value: float) -> str:
    """The usual reading of a PSI value (same as sp500_momentum.monitoring.drift_level)."""
    if pd.isna(value):
        return "n/a"
    return "stable" if value < 0.1 else "moderate" if value < 0.25 else "major"


def latest_drift(monitoring: pd.DataFrame, labels: dict[str, str]) -> tuple[str, pd.DataFrame]:
    """The latest month's PSI per feature, highest first, with its reading."""
    latest = monitoring["month"].max()
    t = monitoring[monitoring["month"] == latest].copy()
    t["feature"] = t["feature"].map(lambda c: labels.get(c, c))
    t["reading"] = t["psi"].map(drift_level)
    return latest, t.sort_values("psi", ascending=False)[["feature", "psi", "reading"]]
