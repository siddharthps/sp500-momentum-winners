"""Model monitoring and the small tables behind the live dashboard (#40).

- **Input drift:** the Population Stability Index (PSI) of a feature, one month against the
  training years. Bins are the reference's deciles; PSI = sum((cur - ref) * ln(cur / ref)) over
  bins. The usual reading: under 0.1 stable, 0.1-0.25 moderate shift, over 0.25 a major shift
  (the model is being asked about a market unlike the one it learned from).
- **The live record:** every tradeable month of live picks whose holding month has ended: each
  strategy's average return from the next open to the following month-end close, SPY's over the
  same span, and how many picks beat it.
- **Strategy returns:** the monthly net returns of the strategies the dashboard draws, from the
  same simulation as notebook 04.
"""

import numpy as np
import pandas as pd

from sp500_momentum import backtest as bt
from sp500_momentum.config import HOLD_MONTHS, RULE_CHECK_FROM, SPLIT

EPS = 1e-4  # floor for an empty bin's share, so the log stays finite


# ---------------------------------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------------------------------


def psi(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    """Population Stability Index of `current` against `reference` (blanks ignored)."""
    ref, cur = reference.dropna().to_numpy(), current.dropna().to_numpy()
    if len(ref) < bins or len(cur) == 0:
        return float("nan")
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:  # (almost) constant reference: no meaningful bins
        return float("nan")
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref)
    c = np.histogram(cur, edges)[0] / len(cur)
    r, c = np.maximum(r, EPS), np.maximum(c, EPS)
    return float(np.sum((c - r) * np.log(c / r)))


def drift_table(
    features: pd.DataFrame,
    columns: list[str],
    ref: tuple[str, str] = (SPLIT["train"][0], SPLIT["validation"][1]),
    since: str = RULE_CHECK_FROM,
) -> pd.DataFrame:
    """PSI of each column, each decision month from `since`, against the decisions in `ref`
    (the training years, 2010-22 by default). Long format: month, feature, psi."""
    d = pd.to_datetime(features["date"])
    reference = features[(d >= ref[0]) & (d <= ref[1])]
    later = features[d >= since]
    rows = []
    for date, g in later.groupby("date"):
        for col in columns:
            rows.append(
                {
                    "month": pd.Timestamp(date).strftime("%Y-%m"),
                    "feature": col,
                    "psi": psi(reference[col], g[col]),
                }
            )
    return pd.DataFrame(rows)


def drift_level(value: float) -> str:
    """The usual reading of a PSI value."""
    if pd.isna(value):
        return "n/a"
    return "stable" if value < 0.1 else "moderate" if value < 0.25 else "major"


# ---------------------------------------------------------------------------------------------
# The live record
# ---------------------------------------------------------------------------------------------


def live_record(
    record: pd.DataFrame | None,
    prices: pd.DataFrame,
    asof: pd.Period,
    tradeable,
    members: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """One row per (decision month, strategy) whose holding month has ended before `asof`, for
    picks made before their trade (`tradeable(made_at, decision_date)`). With `members` (date,
    price_ticker of every member at each decision), `base_rate` is the share of all members that
    beat SPY over the same span: what a random pick would score."""
    cols = ["decision", "strategy", "ret", "spy", "beat", "priced", "picks", "base_rate"]
    if record is None or record.empty:
        return pd.DataFrame(columns=cols)
    ok = record[[tradeable(m, d) for m, d in zip(record["made_at"], record["decision_date"])]]
    if ok.empty:
        return pd.DataFrame(columns=cols)
    months = pd.PeriodIndex(pd.to_datetime(ok["decision_date"]), freq="M")
    p = prices.assign(month=pd.PeriodIndex(prices["month"], freq="M")).set_index(
        ["price_ticker", "month"]
    )

    def ret(ticker: str, m: pd.Period) -> float:
        try:
            return p.loc[(ticker, m + 1), "close_adj"] / p.loc[(ticker, m), "entry_px"] - 1
        except KeyError:
            return float("nan")

    member_months = (
        None
        if members is None
        else members.assign(m=pd.PeriodIndex(pd.to_datetime(members["date"]), freq="M"))
    )
    rows = []
    for m in sorted(set(months[months + 1 < asof])):
        spy = ret("SPY", m)
        base = float("nan")
        if member_months is not None:
            everyone = pd.Series(
                [ret(t, m) for t in member_months.loc[member_months["m"] == m, "price_ticker"]]
            ).dropna()
            base = float((everyone > spy).mean()) if len(everyone) else float("nan")
        for s, g in ok[months == m].groupby("strategy"):
            r = pd.Series([ret(t, m) for t in g["price_ticker"]])
            rows.append(
                {
                    "decision": str(m),
                    "strategy": s,
                    "ret": r.mean(),
                    "spy": spy,
                    "beat": int((r > spy).sum()),
                    "priced": int(r.notna().sum()),
                    "picks": len(g),
                    "base_rate": base,
                }
            )
    return pd.DataFrame(rows, columns=cols)


# ---------------------------------------------------------------------------------------------
# Strategy returns for the dashboard's paths
# ---------------------------------------------------------------------------------------------


def strategy_returns(
    panel: pd.DataFrame,
    prices: pd.DataFrame,
    scores: pd.DataFrame,
    headline: str,
    rf: pd.Series,
) -> pd.DataFrame:
    """Monthly net returns (by month earned) of the strategies the dashboard draws: the headline
    model and the 6-month rule at top 10 (1-month hold, equal weight), the rule chosen on
    2010-22 (by Sharpe net of `rf`, the Fed Funds rate, exactly as in notebook 04), SPY and the
    all-members basket. Same simulation as notebook 04."""
    values = bt.value_matrix(prices)
    bench = bt.benchmark_returns(panel, values)
    out = {}
    for name, col in [("model", headline), ("rule_6m", "ret_6m")]:
        src = bt.merge_scores(panel, scores, [headline]) if name == "model" else panel
        picks = bt.buffered_picks(bt.ranked(src, col), 10, keep=10)
        out[name] = bt.simulate(picks, values, hold=1)["ret"]
    grid_panel = bt.add_rule_preds(panel)
    grid_r, grid_c = bt.run_grid(grid_panel, values, HOLD_MONTHS)
    best, _, _ = bt.selection_check(grid_r, bench, rf, grid_c, RULE_CHECK_FROM)
    out["chosen_rule"] = grid_r[best]
    out["spy"] = bench["spy"]
    out["equal_weight"] = bench["equal_weight"]
    rets = pd.DataFrame(out)
    rets.index = rets.index.astype(str)
    rets.index.name = "month_earned"
    return rets.reset_index()
