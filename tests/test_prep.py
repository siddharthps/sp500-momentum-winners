"""Offline tests for the model data prep: folds, gaps, targets and in-fold preparation."""

import numpy as np
import pandas as pd
import pytest

from sp500_momentum.config import SPLIT
from sp500_momentum.modeling import prep


def _dates(start="2010-01-31", end="2026-09-30", per_month=3):
    me = pd.date_range(start, end, freq="ME")
    return pd.Series(np.repeat(me, per_month))


def test_cv_folds_expand_yearly_with_a_one_month_gap():
    dates = _dates()
    m = pd.PeriodIndex(dates, freq="M")
    folds = prep.cv_folds(dates)
    assert [f.name for f in folds] == [f"cv_{y}" for y in range(2014, 2020)]
    for f in folds:
        assert not set(f.train) & set(f.score)
        last_train, first_score = m[f.train].max(), m[f.score].min()
        assert (first_score - last_train).n >= 2  # December before the scored year is dropped
        assert m[f.train].min() == pd.Period("2010-01", "M")  # expanding from the start
        assert m[f.score].min().month == 1 and m[f.score].max().month == 12  # a whole year


def test_cv_never_touches_the_validation_or_test_blocks():
    dates = _dates()
    end_of_train = pd.Timestamp(SPLIT["train"][1])
    for f in prep.cv_folds(dates):
        assert dates.iloc[np.r_[f.train, f.score]].max() <= end_of_train
    with pytest.raises(ValueError, match="inside the train block"):
        prep.cv_folds(dates, score_years=[2020])


def test_holdout_folds_validation_then_one_test():
    dates = _dates()
    m = pd.PeriodIndex(dates, freq="M")
    h = prep.holdout_folds(dates)
    v, t = h["validation"], h["test"]
    assert m[v.train].max() == pd.Period("2019-11", "M")
    assert (m[v.score].min(), m[v.score].max()) == (
        pd.Period("2020-01", "M"),
        pd.Period("2022-12", "M"),
    )
    assert m[t.train].max() == pd.Period("2022-11", "M")  # train + validation, minus the gap
    assert m[t.score].min() == pd.Period("2023-01", "M")
    assert not set(t.train) & set(t.score)


def test_block_of_follows_split():
    b = prep.block_of(pd.Series(pd.to_datetime(["2019-12-31", "2020-01-31", "2023-01-31"])))
    assert b.tolist() == ["train", "validation", "test"]


def test_excess_decile_is_within_each_month():
    rows = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * 10 + ["2020-02-28"] * 10),
            # February is a crash month: every return is negative, but deciles still span 0-9
            "fwd_excess_1m": list(np.linspace(0.01, 0.10, 10)) + list(np.linspace(-0.5, -0.1, 10)),
        }
    )
    d = prep.excess_decile(rows)
    assert d.iloc[:10].tolist() == list(range(10))
    assert d.iloc[10:].tolist() == list(range(10))


def test_rank_within_month_only_compares_the_same_month():
    X = pd.DataFrame({"ret": [0.1, 0.2, -0.5, -0.4, np.nan], "vix": [20, 20, 40, 40, 40.0]})
    dates = pd.Series(pd.to_datetime(["2020-01-31"] * 2 + ["2020-02-28"] * 3))
    out = prep.rank_within_month(X, dates, ["ret"])
    assert out["ret"].tolist()[:4] == [0.5, 1.0, 0.5, 1.0]  # best in its own month = 1.0
    assert np.isnan(out["ret"].iloc[4])  # blanks stay blank
    assert out["vix"].equals(X["vix"])  # market features untouched


def test_ranker_groups_one_per_date_and_require_sorted_rows():
    dates = pd.Series(pd.to_datetime(["2020-01-31"] * 3 + ["2020-02-28"] * 2))
    assert prep.ranker_groups(dates).tolist() == [3, 2]
    with pytest.raises(ValueError, match="sorted"):
        prep.ranker_groups(dates.iloc[::-1])


def test_preparation_learns_only_from_training_rows():
    train = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0, 100.0], "b": [0.0, 0.0, 1.0, 1.0, 1.0]})
    score = pd.DataFrame({"a": [np.nan, 1000.0], "b": [5.0, 5.0]})
    pipe = prep.preprocessor("impute_clip_scale").fit(train)
    clip = pipe.named_steps["clip"]
    assert clip.upper_[0] == pytest.approx(np.nanquantile(train["a"], 0.99))
    # the score rows' 1000 is clipped to the TRAIN limit, and its blank gets the TRAIN median
    imp = pipe.named_steps["impute"]
    clipped_train_a = np.clip(train["a"], clip.lower_[0], clip.upper_[0])
    assert imp.statistics_[0] == pytest.approx(np.nanmedian(clipped_train_a))
    out = pipe.transform(score)
    assert out.shape == (2, 3)  # a, b, and a "was missing" flag for a
    assert not np.isnan(out).any()


def test_native_preparation_keeps_blanks_for_xgboost():
    assert prep.preprocessor("native") == "passthrough"
    assert set(prep.MODEL_PREP.values()) <= {"native", "impute", "impute_clip_scale"}
    with pytest.raises(ValueError):
        prep.preprocessor("zero_fill")


def test_clip_target_uses_its_own_rows():
    y = pd.Series(np.r_[np.linspace(-0.1, 0.1, 99), 3.0])  # one +300% takeover month
    c = prep.clip_target(y)
    assert c.max() == pytest.approx(y.quantile(0.99))
    assert c.min() == pytest.approx(y.quantile(0.01))
