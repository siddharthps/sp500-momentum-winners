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

import time

from loguru import logger
import pandas as pd
import typer

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

app = typer.Typer(help="The whole pipeline: the final rebuild (#20).")


@app.callback()
def _main():
    """The whole pipeline (keeps `rebuild-all` a named subcommand)."""


# What can't be automated (the #20 checklist's manual parts), before and after the rebuild.
BEFORE_REBUILD = [
    (
        "The AV queue is empty (av-status) and the task is unregistered: "
        "Unregister-ScheduledTask -TaskName sp500-momentum-av-pull -Confirm:$false"
    ),
    "ta_natr dropped from features.py (100 x ta_atr), with its test",
    "The vector-simulation section (#47) added to notebook 04",
    "config.DATA_STATUS changed from 'preview' to final (the last step publishes it)",
]
AFTER_REBUILD = [
    (
        "Every chapter's and the README's numbers refreshed from the rerun notebooks; 'preview' "
        "labels removed"
    ),
    "The book builds: uv run mkdocs build --strict",
    "The dashboard shows the final status (it rereads the public dataset within 6 hours)",
]


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


def rebuild_steps(
    tag: str = "", retrain_models: bool = True, notebooks: bool = True, publish: bool = True
) -> list[tuple[str, object]]:
    """The final rebuild, in order: (name, function) pairs. Each step reads only what the steps
    before it wrote, so the order is the README's "Rerunning after a change" chain."""
    from sp500_momentum import features, hub, monthly, run_notebooks
    from sp500_momentum.config import DATA_STATUS, START_DATE

    steps = [
        ("monthly table", lambda: monthly.build(start=START_DATE)),
        ("features", features.build),
    ]
    if retrain_models:
        steps.append(("models: search, comparison, single test (~1 3/4 h)", retrain))
    if notebooks:
        steps.append(("all notebooks", lambda: run_notebooks.run(prefix="")))
    if publish:
        steps.append(
            (
                f"Hugging Face snapshots{f' (tag {tag})' if tag else ''}",
                lambda: hub.push(target="both", tag=tag, status=DATA_STATUS),
            )
        )
    return steps


def run_steps(steps: list[tuple[str, object]]) -> list[tuple[str, float]]:
    """Run the steps in order, timing each; stop at the first failure (a broken step must not
    feed the ones after it). Returns (name, minutes) for the steps that ran."""
    done = []
    for i, (name, fn) in enumerate(steps, 1):
        t0 = time.time()
        logger.info(f"[{i}/{len(steps)}] {name} ...")
        try:
            fn()
        except (Exception, typer.Exit) as e:  # noqa: BLE001  (stop, report, fail loudly)
            logger.error(f"[{i}/{len(steps)}] {name} FAILED ({type(e).__name__}); stopped here")
            raise typer.Exit(code=1) from None
        minutes = (time.time() - t0) / 60
        done.append((name, minutes))
        logger.success(f"[{i}/{len(steps)}] {name} done in {minutes:.1f} min")
    return done


@app.command("rebuild-all")
def rebuild_all(
    tag: str = typer.Option("", help="Tag the published snapshots (e.g. final-2026-11)"),
    retrain_models: bool = typer.Option(True, "--retrain/--no-retrain", help="Rerun the search"),
    notebooks: bool = typer.Option(True, help="Rerun every notebook (with their output checks)"),
    publish: bool = typer.Option(True, help="Push both Hugging Face datasets at the end"),
    dry_run: bool = typer.Option(False, help="List the steps and the manual checks only"),
):
    """The final rebuild after the Alpha Vantage pull (#20): monthly table -> features -> models
    -> notebooks -> snapshots, timed, stopping at the first failure; then the manual checks."""
    steps = rebuild_steps(tag, retrain_models, notebooks, publish)
    if dry_run:
        print("Before running it:")
        for item in BEFORE_REBUILD:
            print(f"- {item}")
        print("\nThe steps:")
        for i, (name, _) in enumerate(steps, 1):
            print(f"{i}. {name}")
    else:
        done = run_steps(steps)
        logger.success(
            f"Rebuild finished in {sum(m for _, m in done):.0f} min: "
            + "; ".join(f"{n} {m:.1f}" for n, m in done)
        )
    print("\nAfter it, by hand:")
    for item in AFTER_REBUILD:
        print(f"- {item}")


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


if __name__ == "__main__":
    app()
