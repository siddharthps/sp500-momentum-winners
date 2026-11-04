"""Offline tests for scoring, the model specs and the training steps (small synthetic data)."""

import numpy as np
import pandas as pd
import pytest

from sp500_momentum.modeling import evaluate as ev
from sp500_momentum.modeling import prep
from sp500_momentum.modeling.models import SPECS, TimeOrderedMLP


def test_top_n_mask_picks_per_month_and_breaks_ties_by_ticker():
    dates = pd.Series(pd.to_datetime(["2020-01-31"] * 3 + ["2020-02-28"] * 3))
    scores = pd.Series([0.9, 0.5, 0.5, 0.1, 0.2, 0.3])
    tickers = pd.Series(["A", "C", "B", "A", "B", "C"])
    m = ev.top_n_mask(dates, scores, tickers, n=2)
    assert m.tolist() == [True, False, True, False, True, True]  # B beats C on the tie


def test_monthly_scores_and_selection_penalise_unsteady_years():
    dates = pd.Series(pd.to_datetime(["2014-01-31"] * 4 + ["2015-01-30"] * 4))
    scores = pd.Series([4, 3, 2, 1, 4, 3, 2, 1.0])
    tickers = pd.Series(list("ABCDABCD"))
    beat = pd.Series([1, 1, 0, 0, 1, 0, 0, 1])
    excess = pd.Series([0.1, 0.1, -0.1, -0.1, 0.2, -0.1, 0.0, 0.05])
    m = ev.monthly_scores(dates, scores, tickers, beat, excess, n=2)
    assert m["precision"].tolist() == [1.0, 0.5]
    assert m["base_rate"].tolist() == [0.5, 0.5]
    s = ev.summarise(m)
    assert s["precision"] == pytest.approx(0.75)
    assert s["selection_score"] == pytest.approx(0.75 - 0.5 * 0.25)  # mean - half the spread


def test_mlp_stops_on_the_latest_rows():
    fit, stop = TimeOrderedMLP.split_tail(100, 0.15)
    assert stop.min() == fit.max() + 1 and stop.max() == 99 and len(stop) == 15


def _tiny_data(seed=0):
    """A small synthetic ModelData over 2010-2026 with one informative feature."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2010-01-31", "2026-09-30", freq="ME")
    n = 40  # stocks a month, so a top 10 is a real selection
    rows = pd.DataFrame(
        {
            "date": np.repeat(dates, n),
            "ticker": np.tile([f"T{i:02d}" for i in range(n)], len(dates)),
        }
    )
    signal = rng.normal(size=len(rows))
    excess = 0.05 * signal + rng.normal(0, 0.05, len(rows))
    X = pd.DataFrame({"sig": signal, "noise": rng.normal(size=len(rows))}).astype("float32")
    X.loc[::17, "noise"] = np.nan
    feats = rows.assign(fwd_excess_1m=excess)
    y = pd.DataFrame(
        {
            "beat_spy": (excess > 0).astype(int),
            "excess": excess,
            "decile": prep.excess_decile(feats),
        }
    )
    return prep.ModelData(
        rows=rows,
        X_raw=X,
        X_rank=prep.rank_within_month(X, rows["date"], ["sig", "noise"]),
        y=y,
        folds=prep.cv_folds(rows["date"]),
        holdout=prep.holdout_folds(rows["date"]),
    )


@pytest.mark.parametrize("name", ["tree", "logreg", "xgb", "xgb_rank", "xgb_reg"])
def test_every_spec_fits_and_finds_a_planted_signal(name):
    from sp500_momentum.modeling import train

    data = _tiny_data()
    spec = SPECS[name]
    params = {"ranked": False}
    if name.startswith("xgb"):
        params |= {"n_estimators": 30, "max_depth": 2}
    scores, _ = train.fit_and_score(spec, params, data, data.holdout["validation"])
    monthly = train.score_rows(data, scores)
    # the planted signal should put the winners on top far more often than the base rate
    assert monthly["precision"].mean() > monthly["base_rate"].mean() + 0.1


def test_out_of_sample_scores_cover_2014_on_without_overlap():
    from sp500_momentum.modeling import train

    data = _tiny_data()
    train.check_out_of_sample(data)
    scores, _ = train.out_of_sample(SPECS["tree"], {"ranked": False, "max_depth": 2}, data)
    assert scores.index.is_unique
    d = data.rows.loc[scores.index, "date"]
    assert d.min() == pd.Timestamp("2014-01-31") and d.max() == pd.Timestamp("2026-09-30")
    assert set(train.period_of(data, scores.index)) == {"cv", "validation", "test"}


@pytest.mark.parametrize("name", ["logreg", "tree", "xgb"])
def test_feature_importance_names_every_input(name):
    from sp500_momentum.modeling import train

    data = _tiny_data()
    params = {"ranked": False} | ({"n_estimators": 20} if name == "xgb" else {})
    _, pipe = train.fit_and_score(SPECS[name], params, data, data.holdout["validation"])
    imp = ev.feature_importance(pipe, data.X_raw.columns)
    assert imp.sum() == pytest.approx(1.0)
    assert imp.idxmax() == "sig"  # the planted signal is the most important input


def test_best_tries_picks_the_top_selection_score():
    cv = pd.DataFrame(
        {"model": ["a", "a", "b"], "try": [0, 1, 0], "selection_score": [0.50, 0.55, 0.52]}
    )
    b = ev.best_tries(cv)
    assert b.loc["a", "try"] == 1 and b.loc["a", "median_try_score"] == pytest.approx(0.525)


def test_best_params_round_trip_restores_tuples():
    from sp500_momentum.modeling import train

    res = pd.DataFrame(
        {
            "try": [0, 1],
            "selection_score": [0.5, 0.6],
            "params": ['{"hidden_layer_sizes": [32, 16]}', '{"hidden_layer_sizes": [64, 32]}'],
        }
    )
    assert train._restore(train.best_params(res)) == {"hidden_layer_sizes": (64, 32)}
