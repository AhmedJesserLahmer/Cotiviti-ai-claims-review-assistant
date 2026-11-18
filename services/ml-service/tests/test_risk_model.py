import numpy as np
import pandas as pd
import pytest

from ml.risk_model import LABELS, RiskScoreClassifier, tune_cutoffs


def synthetic(n=1200, seed=0):
    rng = np.random.default_rng(seed)
    providers = {f"P{i}": rng.uniform(0.05, 0.6) for i in range(15)}
    rows = []
    for _ in range(n):
        pid = rng.choice(list(providers))
        billed, los, prior = rng.uniform(200, 8000), int(rng.poisson(1)), int(rng.poisson(1.5))
        score = 0.00015 * billed + 0.08 * los + 0.05 * prior + 3.0 * providers[pid] + rng.normal(0, 0.3)
        label = "Low" if score < 1.2 else "Medium" if score < 2.5 else "High"
        rows.append({"billed_amount": billed, "length_of_stay": los, "prior_claims_count": prior,
                     "provider_id": pid, "risk_label": label})
    return pd.DataFrame(rows)


def test_tune_cutoffs_recovers_separating_thresholds():
    score = np.array([0.1, 0.2, 0.9, 1.0, 1.8, 1.9])
    y = np.array([0, 0, 1, 1, 2, 2])
    low, high = tune_cutoffs(score, y, grid=20)
    assert 0.2 < low <= 0.9 and 1.0 < high <= 1.8


def test_learns_provider_effects_and_beats_chance():
    from sklearn.metrics import f1_score

    df = synthetic()
    train, test = df.iloc[:900], df.iloc[900:]
    model = RiskScoreClassifier().fit(train, train["risk_label"])
    assert list(model.classes_) == list(LABELS)
    assert f1_score(test["risk_label"], model.predict(test), average="macro") > 0.7


def test_probabilities_are_ordered_and_unknown_providers_are_handled():
    df = synthetic(600)
    model = RiskScoreClassifier().fit(df, df["risk_label"])
    row = pd.DataFrame([{"billed_amount": 1000.0, "length_of_stay": 0, "prior_claims_count": 0, "provider_id": "NEW"}])
    proba = model.predict_proba(row)[0]
    assert proba.shape == (3,) and proba.sum() == pytest.approx(1.0)
    assert 0 <= model.risk_score(row)[0] <= 2
    assert model.predict(row)[0] in LABELS
