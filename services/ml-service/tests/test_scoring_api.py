import os

import pytest

pytest.importorskip("sklearn")
if not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "ml", "models", "classifier.joblib")):
    pytest.skip("models not trained yet (run: python -m ml.train_models)", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

FEATURES = {
    "billed_amount": 5200.0, "length_of_stay": 3, "prior_claims_count": 2, "treatment_type": "Inpatient",
    "procedure_code": "CPT10010", "patient_age": 67, "provider_avg_claim_amount": 4800.0,
}


def test_score_returns_both_models():
    body = TestClient(main.app).post("/v1/score", json=FEATURES).json()
    assert body["predicted_risk_label"] in {"Low", "Medium", "High"}
    assert body["predicted_paid_amount"] >= 0
    assert abs(sum(body["risk_probabilities"].values()) - 1) < 1e-6


def test_individual_endpoints_agree_with_score():
    client = TestClient(main.app)
    score = client.post("/v1/score", json=FEATURES).json()
    assert client.post("/v1/classify", json=FEATURES).json()["predicted_risk_label"] == score["predicted_risk_label"]
    assert client.post("/v1/predict-payment", json=FEATURES).json()["predicted_paid_amount"] == score["predicted_paid_amount"]


def test_missing_features_rejected():
    assert TestClient(main.app).post("/v1/score", json={"billed_amount": 1}).status_code == 422
