"""The eight candidates (decisions.md, 4 Nov): estimator, preparation, target and search ranges.

Each spec builds a scikit-learn Pipeline: the fold-fitted preparation from `prep.preprocessor`,
then the model. Search ranges are sampled at random with a fixed seed (decided 4 Nov). Every model
also has the switch `ranked`: raw features, or within-month percentiles of the stock-level ones.
The eighth candidate, the average of the others' within-month ranks, needs no fitting (train.py).
"""

import copy
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import loguniform, randint, uniform
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier, XGBRanker, XGBRegressor

from sp500_momentum.modeling.prep import MODEL_PREP, preprocessor

SEED = 0


class TimeOrderedMLP(BaseEstimator, ClassifierMixin):
    """A small MLP averaged over `n_seeds` random starts, with early stopping on the LATEST
    `tail` share of the training rows (rows arrive sorted by date).

    scikit-learn's own early stopping holds out a random sample, which here would mix the
    newest months into training and stop on a slice spread over all years."""

    def __init__(
        self,
        hidden_layer_sizes=(32, 16),
        alpha=1e-4,
        learning_rate_init=1e-3,
        batch_size=512,
        max_epochs=100,
        patience=8,
        tail=0.15,
        n_seeds=5,
        random_state=SEED,
    ):
        self.hidden_layer_sizes = hidden_layer_sizes
        self.alpha = alpha
        self.learning_rate_init = learning_rate_init
        self.batch_size = batch_size
        self.max_epochs = max_epochs
        self.patience = patience
        self.tail = tail
        self.n_seeds = n_seeds
        self.random_state = random_state

    @staticmethod
    def split_tail(n: int, tail: float) -> tuple[np.ndarray, np.ndarray]:
        """(fit rows, stopping rows): the stopping rows are the last `tail` share."""
        cut = round(n * (1 - tail))
        return np.arange(cut), np.arange(cut, n)

    def _fit_one(self, X, y, seed):
        fit, stop = self.split_tail(len(y), self.tail)
        net = MLPClassifier(
            hidden_layer_sizes=self.hidden_layer_sizes,
            alpha=self.alpha,
            learning_rate_init=self.learning_rate_init,
            batch_size=self.batch_size,
            random_state=seed,
        )
        best, best_loss, waited = None, np.inf, 0
        for _ in range(self.max_epochs):
            net.partial_fit(X[fit], y[fit], classes=self.classes_)
            loss = log_loss(y[stop], net.predict_proba(X[stop]), labels=self.classes_)
            if loss < best_loss - 1e-6:
                best, best_loss, waited = copy.deepcopy(net), loss, 0
            else:
                waited += 1
                if waited >= self.patience:
                    break
        return best

    def fit(self, X, y):
        X, y = np.asarray(X, dtype="float32"), np.asarray(y)
        self.classes_ = np.unique(y)
        self.nets_ = [self._fit_one(X, y, self.random_state + k) for k in range(self.n_seeds)]
        return self

    def predict_proba(self, X):
        X = np.asarray(X, dtype="float32")
        return np.mean([n.predict_proba(X) for n in self.nets_], axis=0)

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(axis=1)]


@dataclass(frozen=True)
class ModelSpec:
    name: str
    label: str  # readable name for tables and charts
    target: str  # "beat_spy", "decile" or "excess" (a column of ModelData.y)
    make: callable  # params -> unfitted estimator
    space: dict = field(default_factory=dict)  # search ranges for the estimator's settings
    n_iter: int = 30
    grouped: bool = False  # the ranker needs the month of each row

    @property
    def prep(self) -> str:
        return MODEL_PREP[self.name]

    def pipeline(self, params: dict) -> Pipeline:
        model_params = {k: v for k, v in params.items() if k != "ranked"}
        return Pipeline([("prep", preprocessor(self.prep)), ("model", self.make(model_params))])

    def scores(self, pipe: Pipeline, X) -> np.ndarray:
        """Higher = more likely to be a winner: probability for classifiers, raw for others."""
        if self.target == "beat_spy":
            return pipe.predict_proba(X)[:, 1]
        return pipe.predict(X)


RANKED = {"ranked": [False, True]}
XGB_COMMON = {
    "n_estimators": randint(100, 800),
    "learning_rate": loguniform(0.01, 0.2),
    "max_depth": randint(2, 7),
    "min_child_weight": loguniform(1, 200),
    "subsample": uniform(0.5, 0.5),
    "colsample_bytree": uniform(0.3, 0.7),
    "reg_lambda": loguniform(0.1, 100),
}


def _xgb(cls, **fixed):
    def make(p):
        return cls(tree_method="hist", n_jobs=-1, random_state=SEED, verbosity=0, **fixed, **p)

    return make


SPECS = {
    "tree": ModelSpec(
        "tree",
        "Decision tree",
        "beat_spy",
        lambda p: DecisionTreeClassifier(random_state=SEED, **p),
        # leaf sizes as counts (a float would be read as a share of the rows)
        {
            **RANKED,
            "max_depth": randint(2, 12),
            "min_samples_leaf": [50, 100, 200, 500, 1000, 2000],
        },
    ),
    "rf": ModelSpec(
        "rf",
        "Random forest",
        "beat_spy",
        lambda p: RandomForestClassifier(n_jobs=-1, random_state=SEED, **p),
        {
            **RANKED,
            "n_estimators": randint(200, 600),
            "max_depth": randint(3, 14),
            "min_samples_leaf": [20, 50, 100, 200, 500, 1000],
            "max_features": uniform(0.05, 0.45),
        },
    ),
    "logreg": ModelSpec(
        "logreg",
        "Logistic regression",
        "beat_spy",
        # L2 with lbfgs: saga (needed for L1/elastic net) took ~8 min a try on 235 correlated
        # columns, and L1 would pick one of each near-duplicate pair at random anyway.
        lambda p: LogisticRegression(solver="lbfgs", max_iter=1000, **p),
        {**RANKED, "C": loguniform(1e-4, 10)},
    ),
    "xgb": ModelSpec(
        "xgb",
        "XGBoost, beat or not",
        "beat_spy",
        _xgb(XGBClassifier, objective="binary:logistic", eval_metric="logloss"),
        {**RANKED, **XGB_COMMON},
    ),
    "xgb_rank": ModelSpec(
        "xgb_rank",
        "XGBoost, ranking",
        "decile",
        _xgb(XGBRanker, objective="rank:ndcg"),
        {**RANKED, **XGB_COMMON},
        grouped=True,
    ),
    "xgb_reg": ModelSpec(
        "xgb_reg",
        "XGBoost, by how much",
        "excess",
        _xgb(XGBRegressor, objective="reg:pseudohubererror"),
        {**RANKED, **XGB_COMMON, "huber_slope": loguniform(0.02, 0.3)},
    ),
    "mlp": ModelSpec(
        "mlp",
        "Neural network (MLP)",
        "beat_spy",
        lambda p: TimeOrderedMLP(**p),
        {
            **RANKED,
            "hidden_layer_sizes": [(16,), (32,), (32, 16), (64, 32), (32, 16, 8), (64, 32, 16)],
            "alpha": loguniform(1e-5, 1e-1),
            "learning_rate_init": loguniform(1e-4, 1e-2),
        },
        n_iter=20,
    ),
}
ENSEMBLE = "average"
ENSEMBLE_LABEL = "Average of the models"
