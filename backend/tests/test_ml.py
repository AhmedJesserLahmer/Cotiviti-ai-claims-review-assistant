"""Unit tests for the trained ML models via the inference helpers.

Requires that models have been trained (python -m ml.train_models) — they are
baked into the Docker image, and CI/local runs train first.
"""

import os

import pytest

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "models")

pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(MODELS_DIR, "classifier.joblib")),
    reason="models not trained yet (run: python -m ml.train_models)",
)

SAMPLE_CLAIM = {
    "billed_amount": 5200.0,
    "length_of_stay": 3,
    "prior_claims_count": 2,
    "treatment_type": "Inpatient",
    "procedure_code": "CPT10010",
}
SAMPLE_PATIENT = {"age": 67}


def test_classify_claim_returns_valid_label_and_probs():
    from ml.inference import classify_claim

    label, proba = classify_claim(SAMPLE_CLAIM, SAMPLE_PATIENT)
    assert label in {"Low", "Medium", "High"}
    assert pytest.approx(sum(proba.values()), abs=1e-6) == 1.0
    assert all(0.0 <= v <= 1.0 for v in proba.values())


def test_predict_payment_is_non_negative():
    from ml.inference import predict_payment

    predicted = predict_payment(SAMPLE_CLAIM, provider_avg_claim_amount=4800.0)
    assert isinstance(predicted, float)
    assert predicted >= 0.0


def test_cluster_and_anomaly_models_exist():
    for name in ["cluster_model.joblib", "anomaly_model.joblib", "predictor.joblib"]:
        assert os.path.exists(os.path.join(MODELS_DIR, name)), f"missing {name}"
