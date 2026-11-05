"""The monthly run (#17): fresh data -> the latest month-end's picks.

    uv run python -m sp500_momentum.modeling.predict run              # the whole monthly update
    uv run python -m sp500_momentum.modeling.predict run --no-download  # rebuild + picks only

Steps (decisions.md, 5 Nov):
1. Update the data: membership, removed members' coverage, the active tickers' full price history
   (re-downloaded, never appended: see `dataset yahoo-daily --active-only`), FRED.
2. Rebuild the monthly table and the features.
3. Check the latest month-end before trusting it: it must be the month's real last trading day
   (not a day the download hadn't caught up to), and nearly all members must have a price.
   Otherwise the run fails loudly and writes nothing.
4. Picks, both published and labelled:
   - the headline model, **refitted** on every month with a known result, using the settings
     chosen in tuning (never re-tuned), with the same one-month gap as the backtest;
   - the 6-month rule (the stronger strategy in every test).
5. Save one CSV per decision month and append to the running record (for live monitoring).

A month already done is skipped unless `--force`. Nothing here trades: it's a research output.
"""

import json
import time

from dateutil.easter import easter
import joblib
from loguru import logger
import numpy as np
import pandas as pd
import typer

from sp500_momentum.config import (
    FEATURES_TABLE,
    FRED_START,
    LIVE_MIN_PRICED,
    LIVE_MODEL,
    LIVE_PICKS,
    LIVE_RULE_SIGNAL,
    LIVE_TOP_N,
    MODELS_DIR,
    MONTHLY_PRICES,
    PICKS_DIR,
    PRICE_START,
    SPLIT,
    START_DATE,
)
from sp500_momentum.modeling import prep, train
from sp500_momentum.modeling.models import SPECS

app = typer.Typer(help="The monthly run: fresh data, then next month's picks.")

PICK_COLUMNS = ["decision_date", "strategy", "rank", "ticker", "sector", "score", "made_at"]
STRATEGY_LABELS = {"model": "Headline model", "rule": "Rule: 6-month return"}


@app.callback()
def _main():
    """The monthly run."""


# ---------------------------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------------------------


def _market_holidays(year: int) -> set[pd.Timestamp]:
    """The US exchange holidays that can fall on a month's last weekday: Good Friday, Memorial
    Day (the last Monday of May) and Thanksgiving (the fourth Thursday of November)."""
    good_friday = pd.Timestamp(easter(year)) - pd.Timedelta(days=2)
    may31 = pd.Timestamp(year, 5, 31)
    memorial = may31 - pd.Timedelta(days=(may31.weekday() - 0) % 7)
    nov1 = pd.Timestamp(year, 11, 1)
    thanksgiving = nov1 + pd.Timedelta(days=(3 - nov1.weekday()) % 7 + 21)
    return {good_friday, memorial, thanksgiving}


def last_trading_day(month: pd.Period) -> pd.Timestamp:
    """The month's last weekday that isn't an exchange holiday."""
    day = pd.offsets.BMonthEnd().rollforward(month.to_timestamp())
    holidays = _market_holidays(month.year)
    while day in holidays:
        day -= pd.offsets.BDay(1)
    return day.normalize()


def month_end_problems(
    features: pd.DataFrame, prices: pd.DataFrame, today: pd.Timestamp, min_priced: float
) -> list[str]:
    """Why the latest decision month can't be trusted yet (empty list = fine).

    - The latest decision must be in an earlier month than `today` (a month that's over).
    - It must be the month's last trading day exactly. If Yahoo hadn't delivered the final day
      yet, the "month-end" would be a day early and the picks would use stale prices. (An
      unscheduled market closure on that day would also stop the run: loudly, which is right.)
    - SPY must have a close for that month, and at least `min_priced` of that month's members
      must have a month-end price.
    """
    problems = []
    decision = pd.Timestamp(features["date"].max())
    month = decision.to_period("M")
    if month >= today.to_period("M"):
        problems.append(f"the latest decision {decision:%Y-%m-%d} is in a month that isn't over")
    expected = last_trading_day(month)
    if decision.normalize() != expected:
        problems.append(
            f"the latest decision {decision:%Y-%m-%d} isn't the month's last trading day "
            f"({expected:%Y-%m-%d}): the download may be incomplete"
        )
    spy = prices[prices["price_ticker"] == "SPY"]
    if pd.isna(spy.loc[spy["month"].astype(str) == str(month), "close_adj"]).all():
        problems.append(f"SPY has no month-end close for {month}")
    unknown = sorted(set(features.loc[features["sector"] == "Unknown", "ticker"]))
    if unknown:
        problems.append(
            f"no sector for {', '.join(unknown)} (probably just removed from the index): add them "
            f"to references/removed_sectors.csv, or the features gain a column the model never saw"
        )
    latest = features[features["date"] == decision]
    priced = latest["has_price"].astype(bool).mean() if len(latest) else 0.0
    if priced < min_priced:
        problems.append(
            f"only {priced:.0%} of {len(latest)} members have a price (< {min_priced:.0%})"
        )
    return problems


# ---------------------------------------------------------------------------------------------
# Picks
# ---------------------------------------------------------------------------------------------


def top_picks(rows: pd.DataFrame, score: pd.Series, n: int, strategy: str) -> pd.DataFrame:
    """The n members with the highest score (ties: alphabetical ticker), as pick rows."""
    t = rows.assign(score=score.to_numpy()).dropna(subset=["score"])
    t = t.sort_values(["score", "ticker"], ascending=[False, True]).head(n)
    return pd.DataFrame(
        {
            "decision_date": t["date"].dt.strftime("%Y-%m-%d").to_numpy(),
            "strategy": strategy,
            "rank": np.arange(1, len(t) + 1),
            "ticker": t["ticker"].to_numpy(),
            "sector": t.get("sector", pd.Series(pd.NA, index=t.index)).to_numpy(),
            "score": t["score"].astype("float64").round(6).to_numpy(),  # float32 rounds noisily
        }
    )


def live_rows(features: pd.DataFrame, decision: pd.Timestamp) -> pd.DataFrame:
    """The decision month's members with a month-end price (the next open isn't known yet, so
    `has_price` is the test, not the backtest's `entry_px`)."""
    rows = features[(features["date"] == decision) & features["has_price"].astype(bool)]
    return rows.sort_values("ticker").reset_index(drop=True)


def trained_columns(pipe) -> list[str]:
    """The input columns a fitted pipeline was trained on. A 'passthrough' first step (the XGBoost
    models) can't report them, so ask the first fitted step that can."""
    for _, step in pipe.steps:
        names = getattr(step, "feature_names_in_", None)
        if names is not None:
            return list(names)
    raise ValueError("the pipeline doesn't record its input columns")


def column_problems(features: pd.DataFrame, tuned_columns) -> list[str]:
    """The feature columns must be exactly the ones the model was tuned on (same names, same
    order). A new or missing column means the data changed shape; refitting on it would quietly
    give the model inputs its settings were never chosen for."""
    cols = prep.feature_columns(features.columns)
    tuned = list(tuned_columns)
    if cols == tuned:
        return []
    new, gone = sorted(set(cols) - set(tuned)), sorted(set(tuned) - set(cols))
    return [
        f"feature columns differ from the tuned model's: new {new or '-'}, missing {gone or '-'}"
    ]


def headline_settings(comparison: pd.DataFrame, cv: pd.DataFrame) -> tuple[str, dict]:
    """The headline model (chosen on 2020-22) and its tuned settings, exactly as trained."""
    name = comparison.loc[comparison["headline"].astype(bool), "model"].iloc[0]
    return name, train._restore(train.best_params(cv[cv["model"] == name]))


def refit_and_score(features: pd.DataFrame, name: str, params: dict, decision: pd.Timestamp):
    """Refit the headline on every month with a known result, minus the backtest's one-month
    gap before the scored month, with fixed settings; score the decision month's members."""
    spec = SPECS[name]
    data = prep.load_model_data(features)
    fold = prep.window_fold(
        "live",
        data.rows["date"],
        SPLIT["train"][0],
        f"{decision:%Y-%m-01}",
        f"{decision:%Y-%m-%d}",
    )
    pipe = train.fit_pipeline(spec, params, data, fold.train)
    rows = live_rows(features, decision)
    cols = prep.feature_columns(features.columns)
    X = rows[cols].astype("float32")
    if params.get("ranked", False):
        X = prep.rank_within_month(X, rows["date"], prep.rankable_columns(features.columns))
    scores = pd.Series(spec.scores(pipe, X.astype("float32")), index=rows.index)
    trained_to = data.rows["date"].iloc[fold.train].max()
    return rows, scores, pipe, trained_to


def append_record(record: pd.DataFrame | None, picks: pd.DataFrame) -> pd.DataFrame:
    """The running record with this month's picks, replacing any earlier copy of the same
    decision month (a forced rerun), sorted."""
    if record is None or record.empty:
        out = picks
    else:
        months = set(picks["decision_date"])
        out = pd.concat([record[~record["decision_date"].isin(months)], picks])
    return out.sort_values(["decision_date", "strategy", "rank"]).reset_index(drop=True)[
        PICK_COLUMNS
    ]


# ---------------------------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------------------------


def update_data() -> None:
    """Step 1: fresh membership, coverage, active prices and FRED (about two minutes)."""
    from sp500_momentum import dataset

    dataset.membership()
    dataset.coverage(start=START_DATE)
    dataset.yahoo_daily(start=PRICE_START, refresh=False, active_only=True)
    dataset.fred(start=FRED_START)


def rebuild() -> None:
    """Step 2: the monthly table, then the features."""
    from sp500_momentum import features, monthly

    monthly.build(start=START_DATE)
    features.build()


@app.command()
def run(
    download: bool = typer.Option(True, help="Update the raw data first (off: rebuild only)"),
    force: bool = typer.Option(False, help="Redo a decision month that's already been done"),
):
    """The monthly update: data, rebuild, checks, both strategies' picks."""
    t0 = time.time()
    if download:
        update_data()
    rebuild()

    feats = pd.read_parquet(FEATURES_TABLE)
    prices = pd.read_parquet(MONTHLY_PRICES)
    comparison = pd.read_csv(train.COMPARISON)
    cv = pd.read_csv(train.CV_RESULTS)
    name, params = headline_settings(comparison, cv)
    tuned = trained_columns(joblib.load(MODELS_DIR / f"{name}.joblib"))
    problems = month_end_problems(feats, prices, pd.Timestamp.now(), LIVE_MIN_PRICED)
    problems += column_problems(feats, tuned)
    if problems:
        for p in problems:
            logger.error(p)
        raise typer.Exit(code=1)

    decision = pd.Timestamp(feats["date"].max())
    out_file = PICKS_DIR / f"picks_{decision:%Y-%m}.csv"
    if out_file.exists() and not force:
        logger.info(f"{out_file.name} already exists; nothing to do (use --force to redo it)")
        return

    rows, scores, pipe, trained_to = refit_and_score(feats, name, params, decision)
    joblib.dump(pipe, LIVE_MODEL)

    made_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    picks = pd.concat(
        [
            top_picks(rows, scores, LIVE_TOP_N, "model"),
            top_picks(rows, rows[LIVE_RULE_SIGNAL], LIVE_TOP_N, "rule"),
        ],
        ignore_index=True,
    ).assign(made_at=made_at)[PICK_COLUMNS]
    PICKS_DIR.mkdir(parents=True, exist_ok=True)
    picks.to_csv(out_file, index=False)
    record = pd.read_csv(LIVE_PICKS) if LIVE_PICKS.exists() else None
    append_record(record, picks).to_csv(LIVE_PICKS, index=False)

    summary = "\n".join(
        f"  {STRATEGY_LABELS[s]}: {', '.join(picks.loc[picks['strategy'] == s, 'ticker'])}"
        for s in ["model", "rule"]
    )
    logger.success(
        f"Picks for the month after {decision:%Y-%m-%d} (trade at the next open), in "
        f"{(time.time() - t0) / 60:.1f} min. Model: {name} {json.dumps(params, sort_keys=True)}, "
        f"refitted on decisions to {trained_to:%Y-%m-%d}; {len(rows)} members scored.\n{summary}"
    )


if __name__ == "__main__":
    app()
