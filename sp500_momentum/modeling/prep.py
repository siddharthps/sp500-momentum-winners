"""Model data prep: the feature matrix, targets, time blocks with gaps, CV folds and the
preparation pipelines. #13 imports this; nothing here trains or scores a model.

Decisions (decisions.md, 3-4 Nov):
- Rows: members with a price and a known next-month result, sorted by decision date then ticker.
- Targets: `is_beat_spy_1m` (classifiers), the excess-return decile 0-9 within each month (ranker),
  `fwd_excess_1m` (regressor, clipped to the training fold's 1st/99th percentile).
- Time blocks from SPLIT: train 2010-19, validation 2020-22, test 2023 on.
- Gap: every training window drops its last decision month before the block it's scored on.
- CV (option A): expanding yearly folds inside the train block, scoring 2014-2019. The validation
  block compares the tuned models; the final model is refit on 2010-22 and tested once.
- Within-month percentiles: a second copy of the stock-level features, ranked among that month's
  members. Stateless (it uses only the same month's rows), so it's computed once; whether a model
  uses it is a tuning choice. Market and macro features (one value per month) and flags stay raw.
- Anything that learns from data (medians, clip limits, scaling) is a pipeline step, fitted on a
  fold's training rows only:
    native            XGBoost models (they read blanks directly)
    impute            tree, random forest: median + "was missing" flags
    impute_clip_scale logistic regression, MLP: clip to 1st/99th percentile, median + flags, scale
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sp500_momentum.config import SPLIT
from sp500_momentum.features import feature_sets

FEATURE_SETS = ["PAST_RETURNS", "TA", "STOCK", "CROSS_SECTION", "MARKET", "MACRO", "DUMMIES"]
RAW_ONLY_SETS = {"MARKET", "MACRO", "DUMMIES"}  # same value for every stock in a month, or flags
CV_SCORE_YEARS = range(2014, 2020)  # option A: tune inside the train block
GAP_MONTHS = 1
CLIP_QUANTILES = (0.01, 0.99)
ROW_INFO = ["date", "ticker", "price_ticker", "source", "sector"]

MODEL_PREP = {
    "tree": "impute",
    "rf": "impute",
    "logreg": "impute_clip_scale",
    "mlp": "impute_clip_scale",
    "xgb": "native",
    "xgb_rank": "native",
    "xgb_reg": "native",
}


# ---------------------------------------------------------------------------------------------
# Rows, features and targets
# ---------------------------------------------------------------------------------------------


def feature_columns(columns) -> list[str]:
    """The model's input columns: every named feature set, in a fixed order."""
    sets = feature_sets(columns)
    return [c for name in FEATURE_SETS for c in sets[name]]


def rankable_columns(columns) -> list[str]:
    """Stock-level features (they differ across stocks in a month), the ones that can be ranked."""
    sets = feature_sets(columns)
    return [c for name in FEATURE_SETS if name not in RAW_ONLY_SETS for c in sets[name]]


def model_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Members with a price and a known next-month result, sorted by date then ticker."""
    ok = df["has_price"].astype(bool) & df["is_beat_spy_1m"].notna()
    return df[ok].sort_values(["date", "ticker"]).reset_index(drop=True)


def excess_decile(rows: pd.DataFrame) -> pd.Series:
    """Next-month excess return as a grade 0-9 within each month (9 = the best tenth)."""
    pct = rows.groupby("date")["fwd_excess_1m"].rank(method="first", pct=True)
    return np.ceil(pct * 10).clip(1, 10).astype(int) - 1


def targets(rows: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "beat_spy": rows["is_beat_spy_1m"].astype(int),
            "excess": rows["fwd_excess_1m"].astype(float),
            "decile": excess_decile(rows),
        },
        index=rows.index,
    )


def rank_within_month(X: pd.DataFrame, dates: pd.Series, columns: list[str]) -> pd.DataFrame:
    """Replace `columns` with their percentile among the same month's rows (blanks stay blank).

    Uses only rows from the same decision date, so it can't mix in other periods."""
    out = X.copy()
    out[columns] = X[columns].groupby(dates.to_numpy()).rank(pct=True)
    return out


def ranker_groups(dates: pd.Series) -> np.ndarray:
    """Group sizes for a learning-to-rank model: one group per decision date, in row order.
    The rows must be sorted by date."""
    d = pd.Series(dates).reset_index(drop=True)
    if not d.is_monotonic_increasing:
        raise ValueError("rows must be sorted by date for ranker groups")
    return d.groupby(d, sort=False).size().to_numpy()


# ---------------------------------------------------------------------------------------------
# Time blocks, gaps and folds
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Fold:
    """Row positions to train on and to score on."""

    name: str
    train: np.ndarray
    score: np.ndarray


def _months(dates: pd.Series) -> pd.PeriodIndex:
    return pd.PeriodIndex(pd.to_datetime(dates), freq="M")


def block_of(dates: pd.Series) -> pd.Series:
    """'train', 'validation' or 'test' for each decision date, from SPLIT."""
    d = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
    out = pd.Series(pd.NA, index=d.index, dtype="object")
    for name, (a, b) in SPLIT.items():
        out[(d >= pd.Timestamp(a)) & (d <= pd.Timestamp(b))] = name
    return out


def window_fold(
    name: str, dates: pd.Series, train_from: str, score_from: str, score_to: str
) -> Fold:
    """Train on [train_from, score_from) minus the last GAP_MONTHS decision months; score on
    [score_from, score_to]. A training row's result (next month) then never falls in the months
    being scored, or right next to them."""
    m = _months(dates)
    first_scored = pd.Period(score_from, freq="M")
    train = (m >= pd.Period(train_from, freq="M")) & (m < first_scored - GAP_MONTHS)
    score = (m >= first_scored) & (m <= pd.Period(score_to, freq="M"))
    return Fold(name, np.flatnonzero(train), np.flatnonzero(score))


def cv_folds(dates: pd.Series, score_years=CV_SCORE_YEARS) -> list[Fold]:
    """Expanding yearly folds inside the train block: train from its start to the year before
    (minus the gap), score on one year. Nothing from the validation or test blocks is used."""
    start, end = SPLIT["train"]
    last = pd.Timestamp(end).year
    if max(score_years) > last:
        raise ValueError(f"CV must stay inside the train block (ends {last})")
    return [window_fold(f"cv_{y}", dates, start, f"{y}-01-01", f"{y}-12-31") for y in score_years]


def holdout_folds(dates: pd.Series) -> dict[str, Fold]:
    """`validation`: train on the train block, score 2020-22 (model comparison).
    `test`: train on train + validation, score the test block once (the final result)."""
    train_from = SPLIT["train"][0]
    v_from, v_to = SPLIT["validation"]
    t_from, t_to = SPLIT["test"]
    return {
        "validation": window_fold("validation", dates, train_from, v_from, v_to),
        "test": window_fold("test", dates, train_from, t_from, t_to),
    }


# ---------------------------------------------------------------------------------------------
# Preparation fitted inside each fold
# ---------------------------------------------------------------------------------------------


class QuantileClipper(BaseEstimator, TransformerMixin):
    """Clip each column to the quantiles of the rows it was fitted on (blanks ignored and kept)."""

    def __init__(self, quantiles=CLIP_QUANTILES):
        self.quantiles = quantiles

    def fit(self, X, y=None):
        a = np.asarray(X, dtype="float64")
        self.n_features_in_ = a.shape[1]
        if hasattr(X, "columns"):  # like scikit-learn's transformers: remember the input names
            self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        with np.errstate(all="ignore"):
            self.lower_ = np.nanquantile(a, self.quantiles[0], axis=0)
            self.upper_ = np.nanquantile(a, self.quantiles[1], axis=0)
        return self

    def transform(self, X):
        a = np.asarray(X, dtype="float64")
        return np.clip(a, self.lower_, self.upper_)

    def get_feature_names_out(self, input_features=None):
        """One output per input, same names (works for models saved before this existed)."""
        return np.asarray(input_features, dtype=object)


def preprocessor(kind: str):
    """The preparation for one model family, as an unfitted pipeline (or 'passthrough')."""
    impute = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    if kind == "native":
        return "passthrough"
    if kind == "impute":
        return Pipeline([("impute", impute)])
    if kind == "impute_clip_scale":
        return Pipeline(
            [("clip", QuantileClipper()), ("impute", impute), ("scale", StandardScaler())]
        )
    raise ValueError(f"unknown preparation {kind!r}")


def clip_target(y_train: pd.Series, quantiles=CLIP_QUANTILES) -> pd.Series:
    """The regressor's target, clipped to its own training rows' quantiles."""
    lo, hi = y_train.quantile(list(quantiles))
    return y_train.clip(lo, hi)


# ---------------------------------------------------------------------------------------------
# Everything #13 needs, in one object
# ---------------------------------------------------------------------------------------------


@dataclass
class ModelData:
    rows: pd.DataFrame  # identifiers per row (date, ticker, ...)
    X_raw: pd.DataFrame
    X_rank: pd.DataFrame  # stock-level features as within-month percentiles
    y: pd.DataFrame  # beat_spy, excess, decile
    folds: list[Fold]
    holdout: dict[str, Fold]

    def X(self, ranked: bool) -> pd.DataFrame:
        return self.X_rank if ranked else self.X_raw


def load_model_data(features: pd.DataFrame) -> ModelData:
    """Build the matrices, targets and folds from the feature table."""
    rows = model_rows(features)
    cols = feature_columns(rows.columns)
    X_raw = rows[cols].astype("float32")
    X_rank = rank_within_month(X_raw, rows["date"], rankable_columns(rows.columns)).astype(
        "float32"
    )
    return ModelData(
        rows=rows[[c for c in ROW_INFO if c in rows.columns]],
        X_raw=X_raw,
        X_rank=X_rank,
        y=targets(rows),
        folds=cv_folds(rows["date"]),
        holdout=holdout_folds(rows["date"]),
    )


def describe_folds(data: ModelData) -> pd.DataFrame:
    """One row per fold: training and scoring periods and row counts."""
    out = []
    for f in [*data.folds, *data.holdout.values()]:
        d = data.rows["date"]
        out.append(
            {
                "fold": f.name,
                "train_from": d.iloc[f.train].min().date(),
                "train_to": d.iloc[f.train].max().date(),
                "score_from": d.iloc[f.score].min().date(),
                "score_to": d.iloc[f.score].max().date(),
                "train_rows": len(f.train),
                "score_rows": len(f.score),
                "score_beat_rate": data.y["beat_spy"].iloc[f.score].mean(),
            }
        )
    return pd.DataFrame(out).set_index("fold")
