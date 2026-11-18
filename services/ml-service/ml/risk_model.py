"""Claim risk classifier: ordinal risk score with provider effects and tuned cutoffs.

Why this model (see docs/adr/0010-risk-model.md):

* The risk label is ordinal (Low < Medium < High) and, in the data we have, driven by
  the claim's billed amount, length of stay, prior claims and the *provider's* risk
  level. Procedure code and patient age carry no signal and only add variance.
* The provider's risk is not observable directly. A regularized per-provider effect
  (one-hot provider_id in a multinomial logistic regression) learns it from the
  provider's past reviewed claims; providers never seen in training fall back to the
  average provider.
* Macro-F1 weights the minority classes (Low, High) like the majority one. Instead of
  the argmax, the predicted probabilities are collapsed into an expected-risk score
  and two cutoffs are tuned for macro-F1 on *out-of-fold* scores, so they are never
  fitted to the rows they are evaluated on.

The estimator follows the scikit-learn API (fit / predict / predict_proba / classes_)
so the rest of the service treats it like any classifier.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

LABELS = ("Low", "Medium", "High")
NUMERIC_FEATURES = ["billed_amount", "length_of_stay", "prior_claims_count"]
PROVIDER_FEATURE = "provider_id"
FEATURES = NUMERIC_FEATURES + [PROVIDER_FEATURE]
_ORDINAL = np.arange(len(LABELS), dtype=float)


def _expected_risk(probabilities: np.ndarray) -> np.ndarray:
    return probabilities @ _ORDINAL


def tune_cutoffs(score: np.ndarray, y: np.ndarray, grid: int = 60) -> tuple[float, float]:
    """Cutoffs (low|medium, medium|high) on the risk score maximizing macro-F1."""
    candidates = np.quantile(score, np.linspace(0.02, 0.98, grid))
    best = (-1.0, 0.5, 1.5)
    for i, low in enumerate(candidates):
        for high in candidates[i + 1:]:
            predicted = np.where(score < low, 0, np.where(score < high, 1, 2))
            value = f1_score(y, predicted, average="macro")
            if value > best[0]:
                best = (value, float(low), float(high))
    return best[1], best[2]


class RiskScoreClassifier(ClassifierMixin, BaseEstimator):
    def __init__(self, C: float = 1.0, cutoff_folds: int = 5, random_state: int = 42):
        self.C = C
        self.cutoff_folds = cutoff_folds
        self.random_state = random_state

    def _pipeline(self) -> Pipeline:
        return Pipeline([
            ("features", ColumnTransformer([
                ("numeric", StandardScaler(), NUMERIC_FEATURES),
                ("provider", OneHotEncoder(handle_unknown="ignore"), [PROVIDER_FEATURE]),
            ])),
            ("model", LogisticRegression(C=self.C, max_iter=5000)),
        ])

    @staticmethod
    def _encode(y) -> np.ndarray:
        index = {label: i for i, label in enumerate(LABELS)}
        return np.array([index[label] for label in y])

    def fit(self, X: pd.DataFrame, y):
        X = X[FEATURES]
        y_ord = self._encode(y)

        # Out-of-fold risk scores for the training rows -> cutoffs never see their own row.
        oof = np.zeros(len(X))
        folds = StratifiedKFold(self.cutoff_folds, shuffle=True, random_state=self.random_state)
        for train_idx, score_idx in folds.split(X, y_ord):
            fold_model = self._pipeline().fit(X.iloc[train_idx], y_ord[train_idx])
            oof[score_idx] = _expected_risk(self._ordered_proba(fold_model, X.iloc[score_idx]))
        self.cutoffs_ = tune_cutoffs(oof, y_ord)

        self.pipeline_ = self._pipeline().fit(X, y_ord)
        self.classes_ = np.array(LABELS)
        self.feature_columns_ = list(FEATURES)
        return self

    @staticmethod
    def _ordered_proba(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
        proba = model.predict_proba(X)
        ordered = np.zeros((len(X), len(LABELS)))
        for column, cls in enumerate(model.named_steps["model"].classes_):
            ordered[:, int(cls)] = proba[:, column]
        return ordered

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Class probabilities in LABELS order (Low, Medium, High)."""
        return self._ordered_proba(self.pipeline_, X[FEATURES])

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        """Expected ordinal risk in [0, 2]."""
        return _expected_risk(self.predict_proba(X))

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        low, high = self.cutoffs_
        score = self.risk_score(X)
        return np.array(LABELS)[np.where(score < low, 0, np.where(score < high, 1, 2))]
