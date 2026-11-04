"""Train, tune and score the candidates (#13).

    uv run python -m sp500_momentum.modeling.train run              # all 7 models + the average
    uv run python -m sp500_momentum.modeling.train run --n-iter 3   # a quick smoke run

Steps (decisions.md, 3-4 Nov):
1. Random search per model (fixed seed) over the 6 CV folds (scoring 2014-2019). Each try is
   scored by its top-10 picks; the best setting has the highest mean yearly precision minus half
   its spread across the years.
2. The best setting is refit on the train block (to Nov 2019) and scored on 2020-22, where the
   candidates are compared; the one with the best selection score there is the headline.
3. Every candidate is refit on 2010-22 (to Nov 2022) and scored once on the test block.
4. Out-of-sample scores 2014-2026 for every row: each row is scored only by a model trained before
   it (the best setting's CV fold, the validation fit, or the test fit). The average of the models'
   within-month ranks is the eighth candidate.

Outputs: reports/model_cv_results.csv (every try), reports/model_comparison.csv (per candidate and
period, with the plain rules for reference), data/processed/model_scores.parquet (out-of-sample
scores), models/<name>.joblib (the test fits).
"""

import json
import time

import joblib
from loguru import logger
import numpy as np
import pandas as pd
from sklearn.model_selection import ParameterSampler
import typer

from sp500_momentum.config import FEATURES_TABLE, MODEL_SCORES, MODELS_DIR, REPORTS_DIR
from sp500_momentum.modeling import evaluate as ev
from sp500_momentum.modeling import prep
from sp500_momentum.modeling.models import ENSEMBLE, ENSEMBLE_LABEL, SEED, SPECS, ModelSpec

app = typer.Typer(help="Train, tune and score the models.")

CV_RESULTS = REPORTS_DIR / "model_cv_results.csv"
COMPARISON = REPORTS_DIR / "model_comparison.csv"
RULES = {"rule_mom_1m": "Rule: last month's top 10", "rule_mom_6m": "Rule: 6-month top 10"}


@app.callback()
def _main():
    """Train, tune and score the models."""


# ---------------------------------------------------------------------------------------------
# One fit on one fold
# ---------------------------------------------------------------------------------------------


def fit_and_score(spec: ModelSpec, params: dict, data: prep.ModelData, fold: prep.Fold):
    """Fit on the fold's training rows (preparation included), score its scoring rows."""
    X = data.X(params.get("ranked", False))
    tr, sc = fold.train, fold.score
    y = data.y[spec.target].iloc[tr]
    if spec.target == "excess":
        y = prep.clip_target(y)
    pipe = spec.pipeline(params)
    kw = {}
    if spec.grouped:
        kw["model__qid"] = pd.factorize(data.rows["date"].iloc[tr])[0]
    pipe.fit(X.iloc[tr], y.to_numpy(), **kw)
    return pd.Series(spec.scores(pipe, X.iloc[sc]), index=data.rows.index[sc]), pipe


def score_rows(data: prep.ModelData, scores: pd.Series) -> pd.DataFrame:
    """Monthly top-10 scores for the rows in `scores` (index = row positions)."""
    idx = scores.index
    r, y = data.rows.loc[idx], data.y.loc[idx]
    return ev.monthly_scores(r["date"], scores, r["ticker"], y["beat_spy"], y["excess"])


# ---------------------------------------------------------------------------------------------
# Search, validation, test
# ---------------------------------------------------------------------------------------------


def cv_search(spec: ModelSpec, data: prep.ModelData, n_iter: int | None = None) -> pd.DataFrame:
    """Every sampled setting scored on the CV folds: one row per try."""
    tries = list(ParameterSampler(spec.space, n_iter or spec.n_iter, random_state=SEED))
    rows = []
    for i, params in enumerate(tries):
        t = time.time()
        monthly = pd.concat(
            [score_rows(data, fit_and_score(spec, params, data, f)[0]) for f in data.folds]
        )
        s = ev.summarise(monthly)
        yearly = monthly.groupby(monthly.index.year)["precision"].mean()
        rows.append(
            {
                "model": spec.name,
                "try": i,
                "params": json.dumps(params, default=_jsonable, sort_keys=True),
                **s,
                **{f"precision_{y}": v for y, v in yearly.items()},
                "seconds": round(time.time() - t, 1),
            }
        )
        logger.info(
            f"{spec.name} try {i + 1}/{len(tries)}: score {s['selection_score']:.4f} "
            f"(precision {s['precision']:.4f}, {rows[-1]['seconds']}s)"
        )
    return pd.DataFrame(rows)


def best_params(results: pd.DataFrame) -> dict:
    best = results.sort_values(["selection_score", "try"], ascending=[False, True]).iloc[0]
    return json.loads(best["params"])


def _jsonable(v):
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, tuple):
        return list(v)
    raise TypeError(type(v))


def _restore(params: dict) -> dict:
    """JSON turns tuples into lists; the MLP's layer sizes must be a tuple again."""
    p = dict(params)
    if isinstance(p.get("hidden_layer_sizes"), list):
        p["hidden_layer_sizes"] = tuple(p["hidden_layer_sizes"])
    return p


def out_of_sample(spec: ModelSpec, params: dict, data: prep.ModelData):
    """Scores for 2014 on, each row from a model trained before it, plus the test-block fit."""
    parts = [fit_and_score(spec, params, data, f)[0] for f in data.folds]
    parts.append(fit_and_score(spec, params, data, data.holdout["validation"])[0])
    test_scores, test_pipe = fit_and_score(spec, params, data, data.holdout["test"])
    parts.append(test_scores)
    return pd.concat(parts).sort_index(), test_pipe


def check_out_of_sample(data: prep.ModelData) -> None:
    """Every scored row's model was trained only on decisions at least 2 months earlier."""
    d = data.rows["date"].dt.to_period("M")
    for f in [*data.folds, *data.holdout.values()]:
        gap = (d.iloc[f.score].min() - d.iloc[f.train].max()).n
        if gap < prep.GAP_MONTHS + 1:
            raise AssertionError(f"{f.name}: training ends {gap} month(s) before scoring")


def period_of(data: prep.ModelData, idx) -> pd.Series:
    d = data.rows.loc[idx, "date"]
    block = prep.block_of(d).set_axis(idx)
    return block.where(block != "train", "cv")


def summaries(data: prep.ModelData, scores: pd.DataFrame) -> pd.DataFrame:
    """Per candidate and period (cv 2014-19, validation, test): the headline numbers."""
    period = period_of(data, scores.index)
    rows = []
    for name in scores.columns:
        for p in ["cv", "validation", "test"]:
            s = scores.loc[period == p, name].dropna()
            if len(s):
                rows.append({"model": name, "period": p, **ev.summarise(score_rows(data, s))})
    return pd.DataFrame(rows)


def rule_scores(features: pd.DataFrame, data: prep.ModelData, idx) -> pd.DataFrame:
    """The plain rules as scores on the same rows (their past return), for reference."""
    keyed = data.rows.loc[idx, ["date", "ticker"]]
    f = features.set_index(["date", "ticker"])[["ret_1m", "ret_6m"]]
    vals = f.reindex(pd.MultiIndex.from_frame(keyed)).set_axis(idx)
    return pd.DataFrame({"rule_mom_1m": vals["ret_1m"], "rule_mom_6m": vals["ret_6m"]})


# ---------------------------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------------------------


@app.command()
def run(
    n_iter: int = typer.Option(0, help="Tries per model (0 = each model's own budget)"),
    models: str = typer.Option("", help="Comma-separated subset, e.g. 'tree,logreg'"),
):
    """Tune every model on the CV folds, compare on 2020-22, test once, save everything."""
    t0 = time.time()
    features = pd.read_parquet(FEATURES_TABLE)
    data = prep.load_model_data(features)
    check_out_of_sample(data)
    names = [m for m in models.split(",") if m] or list(SPECS)
    logger.info(f"{len(data.rows):,} rows; folds:\n{prep.describe_folds(data).to_string()}")

    cv_all, oos, chosen = [], {}, {}
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for name in names:
        spec = SPECS[name]
        t = time.time()
        res = cv_search(spec, data, n_iter or None)
        cv_all.append(res)
        params = _restore(best_params(res))
        chosen[name] = params
        oos[name], pipe = out_of_sample(spec, params, data)
        joblib.dump(pipe, MODELS_DIR / f"{name}.joblib")
        logger.success(f"{name}: best {params} ({(time.time() - t) / 60:.1f} min)")

    scores = pd.DataFrame(oos)
    ranks = pd.DataFrame(
        {n: ev.within_month_rank(data.rows.loc[scores.index, "date"], scores[n]) for n in scores}
    )
    scores[ENSEMBLE] = ranks.mean(axis=1)
    rules = rule_scores(features, data, scores.index)
    table = summaries(data, pd.concat([scores, rules], axis=1))
    labels = {**{n: SPECS[n].label for n in names}, ENSEMBLE: ENSEMBLE_LABEL, **RULES}
    table.insert(1, "label", table["model"].map(labels))
    table["params"] = table["model"].map(
        lambda n: json.dumps(chosen.get(n, {}), default=_jsonable)
    )

    # The headline: the candidate (not a rule) with the best selection score on 2020-22.
    val = table[(table["period"] == "validation") & ~table["model"].str.startswith("rule_")]
    headline = val.sort_values("selection_score", ascending=False)["model"].iloc[0]
    table["headline"] = table["model"] == headline

    pd.concat(cv_all).to_csv(CV_RESULTS, index=False)
    table.to_csv(COMPARISON, index=False)
    out = data.rows.loc[scores.index, ["date", "ticker", "price_ticker"]].copy()
    out["period"] = period_of(data, scores.index)
    out = pd.concat([out, scores], axis=1)
    MODEL_SCORES.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(MODEL_SCORES, index=False)
    # Test-period numbers are not logged: they're looked at once, in the notebook, not on every
    # development run.
    seen = table[table["period"] != "test"]
    logger.success(
        f"Done in {(time.time() - t0) / 60:.1f} min. Headline (chosen on 2020-22): "
        f"{labels[headline]}.\n"
        f"{seen.pivot_table(index='label', columns='period', values='precision').round(4)}"
    )


if __name__ == "__main__":
    app()
