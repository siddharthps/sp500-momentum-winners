"""Exploratory analysis: pure functions that turn the tables into summary tables.

The notebooks call these and show the results; the charts are in `plots.py`.

Rule for anything that could steer modelling choices (feature signal, stability, correlations):
use decisions up to RESEARCH_END only, so the test period stays unseen. Plain descriptions of the
target, and the preview of the plain rule (which fits nothing), may cover every year.
"""

import numpy as np
import pandas as pd

from sp500_momentum.config import RESEARCH_END

# ---------------------------------------------------------------------------------------------
# Data overview
# ---------------------------------------------------------------------------------------------


def coverage_by_year(coverage: pd.DataFrame) -> pd.DataFrame:
    """Average members and share priced per year, from the monthly coverage table."""
    c = coverage.copy()
    c["year"] = pd.to_datetime(c["date"]).dt.year
    out = c.groupby("year").agg(
        members=("members", "mean"),
        priced_share=("priced_pct", "mean"),
        from_alphavantage=("alphavantage", "mean"),
    )
    return out.round({"members": 0, "priced_share": 3, "from_alphavantage": 1})


def removal_gap(coverage_removed: pd.DataFrame, suspects: set[str]) -> pd.DataFrame:
    """Removed members by reason: how many Yahoo covers vs how many need another source.

    A Yahoo series that failed the volume check (another security reused the ticker) counts as
    missing.
    """
    c = coverage_removed.copy()
    ok = c["yahoo_ok"].astype(bool) & ~c["ticker"].isin(suspects)
    c["on_yahoo"] = np.where(ok, "on_yahoo", "missing")
    t = pd.crosstab(c["reason_cat"], c["on_yahoo"], margins=True, margins_name="total")
    return t[["total", "on_yahoo", "missing"]].sort_values("total", ascending=False)


# ---------------------------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------------------------


def _with_target(df: pd.DataFrame, hold: int = 1) -> pd.DataFrame:
    return df[df["has_price"] & df[f"fwd_ret_{hold}m"].notna()]


def beat_rate_by_year(df: pd.DataFrame, hold: int = 1) -> pd.DataFrame:
    """Per year: rows, share of member-months that beat SPY, mean and median excess return."""
    t = _with_target(df, hold).assign(year=lambda d: d["date"].dt.year)
    ex = f"fwd_excess_{hold}m"
    return t.groupby("year").agg(
        rows=(ex, "size"),
        beat_rate=(f"is_beat_spy_{hold}m", "mean"),
        mean_excess=(ex, "mean"),
        median_excess=(ex, "median"),
    )


def excess_quantiles(df: pd.DataFrame, holds=(1, 3, 6, 12)) -> pd.DataFrame:
    """Distribution of excess returns over SPY, per hold period."""
    qs = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
    rows = {}
    for h in holds:
        s = _with_target(df, h)[f"fwd_excess_{h}m"]
        r = s.quantile(qs)
        r.index = [f"p{int(q * 100)}" for q in qs]
        r["mean"], r["beat_rate"], r["rows"] = s.mean(), (s > 0).mean(), len(s)
        rows[f"{h}m"] = r
    return pd.DataFrame(rows).T


def truncation_by_hold(df: pd.DataFrame, holds=(1, 3, 6, 12)) -> pd.DataFrame:
    """Share of positions whose prices ended during the hold (delisted, valued at last price)."""
    out = {}
    for h in holds:
        t = _with_target(df, h)
        out[f"{h}m"] = {
            "rows": len(t),
            "cut_short": int(t[f"fwd_trunc_{h}m"].sum()),
            "share": t[f"fwd_trunc_{h}m"].mean(),
        }
    return pd.DataFrame(out).T


# ---------------------------------------------------------------------------------------------
# Feature signal (research period only)
# ---------------------------------------------------------------------------------------------


def research_rows(df: pd.DataFrame, end: str = RESEARCH_END, hold: int = 1) -> pd.DataFrame:
    """Priced rows with a known target, decided on or before `end`."""
    t = _with_target(df, hold)
    return t[t["date"] <= pd.Timestamp(end)]


def monthly_ic(df: pd.DataFrame, feature: str, target: str = "fwd_excess_1m") -> pd.Series:
    """Spearman rank correlation between a feature and the target, within each month.

    Months where the feature doesn't vary across stocks (market and macro features) are skipped:
    a value shared by every stock can't rank them.
    """
    s = df[["date", feature, target]].dropna()
    r = s.groupby("date")[[feature, target]].rank()
    r["date"] = s["date"]
    ok = s.groupby("date")[feature].transform("nunique") > 2
    r = r[ok]
    return r.groupby("date").apply(lambda g: g[feature].corr(g[target])).dropna()


def information_coefficients(
    df: pd.DataFrame, features: list[str], target: str = "fwd_excess_1m"
) -> pd.DataFrame:
    """Per feature: mean monthly IC, its spread, t-statistic, and share of months with IC > 0."""
    rows = {}
    for f in features:
        ic = monthly_ic(df, f, target)
        if len(ic) < 12:
            continue
        rows[f] = {
            "ic_mean": ic.mean(),
            "ic_std": ic.std(),
            "t_stat": ic.mean() / (ic.std() / np.sqrt(len(ic))),
            "positive_months": (ic > 0).mean(),
            "months": len(ic),
        }
    out = pd.DataFrame(rows).T
    return out.reindex(out["ic_mean"].abs().sort_values(ascending=False).index)


def distinct_signals(ic: pd.DataFrame) -> pd.DataFrame:
    """Collapse features with an identical monthly IC (the same signal under different names, e.g.
    a return and its rank) into one row, keeping the first and listing the others in `same_as`."""
    key = ic["ic_mean"].round(8).astype(str) + "|" + ic["ic_std"].round(8).astype(str)
    groups = ic.groupby(key, sort=False).groups
    keep, same = [], {}
    for idx in groups.values():
        first, *rest = list(idx)
        keep.append(first)
        same[first] = rest
    out = ic.loc[keep].copy()
    out["same_as"] = [same[i] for i in out.index]
    return out


def ic_by_group(ic: pd.DataFrame, sets: dict[str, list[str]]) -> pd.DataFrame:
    """Average absolute IC and the strongest feature, per feature set."""
    rows = {}
    for name, cols in sets.items():
        sub = ic.reindex([c for c in cols if c in ic.index]).dropna(how="all")
        if sub.empty:
            continue
        best = sub["ic_mean"].abs().idxmax()
        rows[name] = {
            "features_with_ic": len(sub),
            "mean_abs_ic": sub["ic_mean"].abs().mean(),
            "strongest": best,
            "strongest_ic": sub.loc[best, "ic_mean"],
        }
    return pd.DataFrame(rows).T.sort_values("mean_abs_ic", ascending=False)


def ic_by_period(
    df: pd.DataFrame, features: list[str], periods: dict[str, tuple[str, str]]
) -> pd.DataFrame:
    """Mean IC of each feature in each sub-period: does the sign hold up over time?"""
    out = {}
    for name, (a, b) in periods.items():
        part = df[(df["date"] >= pd.Timestamp(a)) & (df["date"] <= pd.Timestamp(b))]
        out[name] = {f: monthly_ic(part, f).mean() for f in features}
    return pd.DataFrame(out)


def correlated_pairs(
    df: pd.DataFrame, features: list[str], threshold: float = 0.9
) -> pd.DataFrame:
    """Feature pairs whose Spearman correlation (pooled over the rows) is above `threshold`."""
    x = df[features].rank()
    c = x.corr()
    upper = c.where(np.triu(np.ones(c.shape, dtype=bool), k=1))
    pairs = upper.stack().rename("rho").reset_index()
    pairs.columns = ["feature_a", "feature_b", "rho"]
    pairs = pairs[pairs["rho"].abs() >= threshold]
    return pairs.reindex(pairs["rho"].abs().sort_values(ascending=False).index).reset_index(
        drop=True
    )


def winners_spread(df: pd.DataFrame, signal: str = "ret_1m", top_n: int = 10) -> pd.Series:
    """Each month: mean next-month excess return of the top-N by `signal` minus that of all
    members. The payoff of 'buy last month's winners' as a time series."""

    def one(g):
        return g.nlargest(top_n, signal)["fwd_excess_1m"].mean() - g["fwd_excess_1m"].mean()

    return df.dropna(subset=[signal]).groupby("date")[[signal, "fwd_excess_1m"]].apply(one)


def regime_correlations(df: pd.DataFrame, spread: pd.Series, features: list[str]) -> pd.Series:
    """Correlation of each market-wide feature (one value per month) with the winners' spread."""
    monthly = df.groupby("date")[features].first().reindex(spread.index)
    return monthly.corrwith(spread, method="spearman").sort_values(key=abs, ascending=False)


# ---------------------------------------------------------------------------------------------
# A first look at the plain rule (preview: no costs, no staggering, 1-month hold)
# ---------------------------------------------------------------------------------------------


def plain_rule_returns(
    df: pd.DataFrame, signal: str = "ret_1m", top_ns=(1, 5, 10)
) -> pd.DataFrame:
    """Monthly returns of: the top-N members by `signal` (equal weight, 1-month hold), SPY, and an
    equal-weight basket of all members. Uses the targets, so a stock delisted during the month is
    valued at its last price."""
    t = _with_target(df, 1).dropna(subset=[signal])
    g = t.groupby("date")
    out = pd.DataFrame(
        {
            f"top_{n}": g[[signal, "fwd_ret_1m"]].apply(
                lambda x, n=n: x.nlargest(n, signal)["fwd_ret_1m"].mean()
            )
            for n in top_ns
        }
    )
    out["spy"] = g["spy_fwd_ret_1m"].first()
    out["equal_weight"] = g["fwd_ret_1m"].mean()
    return out


def performance_summary(monthly: pd.DataFrame, benchmark: str = "spy") -> pd.DataFrame:
    """CAGR, volatility, Sharpe (no risk-free rate: a preview), max drawdown, share of months
    beating the benchmark, and growth of $1."""
    rows = {}
    years = len(monthly) / 12
    for col in monthly:
        r = monthly[col].dropna()
        growth = (1 + r).cumprod()
        dd = growth / growth.cummax() - 1
        rows[col] = {
            "cagr": growth.iloc[-1] ** (1 / years) - 1,
            "volatility": r.std() * np.sqrt(12),
            "sharpe": r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else np.nan,
            "max_drawdown": dd.min(),
            "beats_benchmark": (r > monthly[benchmark]).mean() if col != benchmark else np.nan,
            "growth_of_1": growth.iloc[-1],
        }
    return pd.DataFrame(rows).T
