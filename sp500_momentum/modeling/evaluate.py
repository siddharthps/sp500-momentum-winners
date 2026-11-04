"""Scoring model output the way the strategy uses it: each month's top-N picks.

A model only has to ORDER stocks well within a month, so classifiers (probabilities), the ranker
and the regressor (arbitrary scores) are all judged the same way (decisions.md, B4):
- precision: share of the month's top N that beat SPY next month, next to that month's base rate;
- excess: their average return over SPY.
Settings are chosen by the mean of the yearly precision minus half its spread across years
(decided 4 Nov), so a setting that works every year beats one that shines once.
"""

import pandas as pd

TOP_N = 10
SPREAD_PENALTY = 0.5


def top_n_mask(dates: pd.Series, scores: pd.Series, tickers: pd.Series, n: int) -> pd.Series:
    """True for each month's n highest scores. Ties go to the alphabetically first ticker, so
    the picks never depend on row order."""
    d = pd.DataFrame({"date": dates.to_numpy(), "s": scores.to_numpy(), "t": tickers.to_numpy()})
    d = d.sort_values(["date", "s", "t"], ascending=[True, False, True])
    d["k"] = d.groupby("date").cumcount()
    return (d["k"] < n).sort_index().set_axis(dates.index)


def monthly_scores(
    dates: pd.Series,
    scores: pd.Series,
    tickers: pd.Series,
    beat: pd.Series,
    excess: pd.Series,
    n: int = TOP_N,
) -> pd.DataFrame:
    """One row per month: precision and excess return of the top n, and the month's base rate."""
    pick = top_n_mask(dates, scores, tickers, n)
    d = pd.DataFrame({"date": dates, "pick": pick, "beat": beat, "excess": excess})
    g = d.groupby("date")
    top = d[d["pick"]].groupby("date")
    return pd.DataFrame(
        {
            "precision": top["beat"].mean(),
            "excess": top["excess"].mean(),
            "base_rate": g["beat"].mean(),
            "picks": top.size(),
        }
    )


def summarise(monthly: pd.DataFrame) -> dict:
    """Headline numbers over a set of months, and the selection score."""
    yearly = monthly.groupby(monthly.index.year)["precision"].mean()
    spread = yearly.std(ddof=0) if len(yearly) > 1 else 0.0
    return {
        "precision": monthly["precision"].mean(),
        "base_rate": monthly["base_rate"].mean(),
        "lift": monthly["precision"].mean() - monthly["base_rate"].mean(),
        "excess": monthly["excess"].mean(),
        "yearly_min": yearly.min(),
        "yearly_spread": spread,
        "selection_score": yearly.mean() - SPREAD_PENALTY * spread,
        "months": len(monthly),
    }


def best_tries(cv: pd.DataFrame) -> pd.DataFrame:
    """Each model's best try, plus how much tuning mattered: the best score against the median
    try's (a big gap on a short history is a warning sign of fitting the CV years)."""
    ranked = cv.sort_values(["model", "selection_score", "try"], ascending=[True, False, True])
    best = ranked.groupby("model").head(1).set_index("model")
    best["median_try_score"] = cv.groupby("model")["selection_score"].median()
    best["tries"] = cv.groupby("model").size()
    return best


def feature_importance(pipe, columns) -> pd.Series | None:
    """Importance per input column of a fitted pipeline, summing to 1: tree importances, or the
    size of logistic-regression coefficients (inputs are scaled). None for the MLP."""
    model = pipe.named_steps["model"]
    prep_step = pipe.named_steps["prep"]
    names = (
        list(columns) if prep_step == "passthrough" else prep_step.get_feature_names_out(columns)
    )
    if hasattr(model, "feature_importances_"):
        vals = model.feature_importances_
    elif hasattr(model, "coef_"):
        vals = abs(model.coef_[0])
    else:
        return None
    s = pd.Series(vals, index=names)
    return s / s.sum()


def within_month_rank(dates: pd.Series, scores: pd.Series) -> pd.Series:
    """Each score's percentile within its month (for averaging models with different scales)."""
    return scores.groupby(dates.to_numpy()).rank(pct=True)
