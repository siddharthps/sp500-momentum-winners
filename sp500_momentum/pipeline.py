"""The whole workflow as five calls, for the run-all notebook (#19).

    get_data(regime) -> transform() -> latest_picks() -> backtest_summary() -> (show the trades)

It reuses the monthly run's own functions (`modeling.predict`), so the notebook can't drift from
what the scheduled job does, but it has **no side effects** beyond rebuilding `data/`: it sends no
Telegram message, pushes nothing to Hugging Face, and never writes the live picks record.

Data regimes:
- "local":    use the files already on disk (offline, deterministic; the committed notebook's choice)
- "hub":      pull the private Hugging Face snapshot first (needs HF_TOKEN with access)
- "download": refresh membership, coverage, active prices and FRED from the sources (no Alpha
              Vantage: the delisted companies' download is a one-off)

The full model search (~1 3/4 h) is not part of it: `retrain=True` runs it, otherwise the tuned
settings are reused, as the live system does.
"""

import pandas as pd

from sp500_momentum import backtest as bt
from sp500_momentum.config import (
    FEATURES_TABLE,
    FRED_DIR,
    LIVE_MIN_PRICED,
    LIVE_RULE_SIGNAL,
    LIVE_TOP_N,
    MODEL_SCORES,
    MONTHLY_PANEL,
    MONTHLY_PRICES,
    RULE_CHECK_FROM,
    SPLIT,
)

REGIMES = ("local", "hub", "download")


def get_data(regime: str = "local") -> str:
    """Step 1: make sure the raw data is in place; returns what was done."""
    if regime not in REGIMES:
        raise ValueError(f"regime must be one of {REGIMES}")
    if regime == "hub":
        from sp500_momentum import hub

        hub.pull_snapshot()
        return "pulled the private Hugging Face snapshot"
    if regime == "download":
        from sp500_momentum.modeling import predict

        predict.update_data()
        return "downloaded membership, coverage, active prices and FRED"
    return "used the files already on disk"


def transform() -> dict:
    """Step 2: rebuild the monthly table and the features; returns their sizes."""
    from sp500_momentum.features import feature_sets
    from sp500_momentum.modeling import predict

    predict.rebuild()
    panel = pd.read_parquet(MONTHLY_PANEL, columns=["date", "ticker", "has_price"])
    feats = pd.read_parquet(FEATURES_TABLE)
    sets = feature_sets(feats.columns)
    return {
        "member-months": len(panel),
        "month-ends": panel["date"].nunique(),
        "first": f"{panel['date'].min():%Y-%m-%d}",
        "latest": f"{panel['date'].max():%Y-%m-%d}",
        "priced": float(panel["has_price"].astype(bool).mean()),
        "feature sets": {k: len(v) for k, v in sets.items()},
    }


def retrain(n_iter: int = 0) -> None:
    """Optional: the full model search and the single test (~1 3/4 h). Off by default."""
    from sp500_momentum.modeling import train

    train.run(n_iter=n_iter, models="")


def latest_picks() -> tuple[pd.DataFrame, dict]:
    """Steps 3 and 5: refit the headline with its tuned settings on every month with a known
    result (the monthly run's own code), score the latest month-end, and take both strategies'
    top N. Nothing is saved or sent."""
    import joblib

    from sp500_momentum.config import MODELS_DIR
    from sp500_momentum.modeling import predict, train

    feats = pd.read_parquet(FEATURES_TABLE)
    prices = pd.read_parquet(MONTHLY_PRICES)
    name, params = predict.headline_settings(
        pd.read_csv(train.COMPARISON), pd.read_csv(train.CV_RESULTS)
    )
    tuned = predict.trained_columns(joblib.load(MODELS_DIR / f"{name}.joblib"))
    problems = predict.month_end_problems(feats, prices, pd.Timestamp.now(), LIVE_MIN_PRICED)
    problems += predict.column_problems(feats, tuned)
    decision = pd.Timestamp(feats["date"].max())
    rows, scores, _, trained_to = predict.refit_and_score(feats, name, params, decision)
    picks = pd.concat(
        [
            predict.top_picks(rows, scores, LIVE_TOP_N, "model"),
            predict.top_picks(rows, rows[LIVE_RULE_SIGNAL], LIVE_TOP_N, "rule"),
        ],
        ignore_index=True,
    )
    info = {
        "model": name,
        "decision": f"{decision:%Y-%m-%d}",
        "trade at the next open": f"{decision + pd.offsets.BDay(1):%a %d %b %Y}",
        "refitted on decisions to": f"{trained_to:%Y-%m-%d}",
        "members scored": len(rows),
        "checks": problems or "all passed",
    }
    return picks, info


def backtest_summary() -> pd.DataFrame:
    """Step 4: the strategies' results on 2020-22 and the test years (the same simulation as
    notebook 04): $10,000 grown, yearly return, Sharpe ratio, worst fall, against SPY."""
    from sp500_momentum import monitoring
    from sp500_momentum.modeling import train

    comparison = pd.read_csv(train.COMPARISON)
    headline = comparison.loc[comparison["headline"].astype(bool), "model"].iloc[0]
    rf = bt.risk_free(pd.read_csv(FRED_DIR / "FEDFUNDS.csv"))
    rets = monitoring.strategy_returns(
        pd.read_parquet(MONTHLY_PANEL),
        pd.read_parquet(MONTHLY_PRICES),
        pd.read_parquet(MODEL_SCORES),
        headline,
        rf,
    ).set_index("month_earned")
    rets.index = pd.PeriodIndex(rets.index, freq="M")
    periods = {
        "2020–2022": (SPLIT["validation"][0], RULE_CHECK_FROM),
        "test years": (RULE_CHECK_FROM, None),
    }
    names = {
        "model": "Headline model, top 10",
        "rule_6m": "Rule: 6-month top 10",
        "chosen_rule": "Chosen rule (top 5, 6-month, held 6)",
        "spy": "SPY",
    }
    rows = []
    for period, (start, end) in periods.items():
        w = bt.window(rets, start, end)
        for col, label in names.items():
            p = bt.performance(w[col], w["spy"], rf)
            rows.append(
                {
                    "period": period,
                    "strategy": label,
                    "$10,000 became": bt.dollars(w[col])["end_value"],
                    "yearly return": p["cagr"],
                    "Sharpe": p["sharpe"],
                    "worst fall": p["max_drawdown"],
                }
            )
    return pd.DataFrame(rows).set_index(["period", "strategy"])
