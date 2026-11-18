import pytest

pytest.importorskip("sklearn")

from ml import registry  # noqa: E402

try:
    registry.current_version()
except registry.ModelNotFoundError:
    pytest.skip("models not trained yet (run: python -m ml.train_models)", allow_module_level=True)

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

FEATURES = {
    "billed_amount": 5200.0, "length_of_stay": 3, "prior_claims_count": 2, "treatment_type": "Inpatient",
    "procedure_code": "CPT10010", "patient_age": 67, "provider_avg_claim_amount": 4800.0,
}


def test_score_returns_both_models():
    body = TestClient(main.app).post("/v1/score", json=FEATURES).json()
    assert body["predicted_risk_label"] in {"Low", "Medium", "High"}
    assert body["predicted_paid_amount"] >= 0
    assert abs(sum(body["risk_probabilities"].values()) - 1) < 1e-6
    assert body["model_version"] == registry.current_version()


def test_models_endpoint_lists_active_version():
    body = TestClient(main.app).get("/v1/models").json()
    assert body["active"] == registry.current_version()
    assert any(v["active"] for v in body["versions"])


def test_individual_endpoints_agree_with_score():
    client = TestClient(main.app)
    score = client.post("/v1/score", json=FEATURES).json()
    assert client.post("/v1/classify", json=FEATURES).json()["predicted_risk_label"] == score["predicted_risk_label"]
    assert client.post("/v1/predict-payment", json=FEATURES).json()["predicted_paid_amount"] == score["predicted_paid_amount"]


def test_missing_features_rejected():
    assert TestClient(main.app).post("/v1/score", json={"billed_amount": 1}).status_code == 422


def test_in_distribution_claim_has_no_ood_flags():
    assert TestClient(main.app).post("/v1/score", json=FEATURES).json()["ood_flags"] == []


def test_out_of_distribution_claim_is_flagged():
    odd = {**FEATURES, "billed_amount": 9_000_000, "treatment_type": "Teleportation"}
    flags = TestClient(main.app).post("/v1/score", json=odd).json()["ood_flags"]
    assert any("billed_amount" in f for f in flags) and any("treatment_type" in f for f in flags)


@pytest.mark.parametrize("field, value", [("billed_amount", -5), ("patient_age", 300), ("length_of_stay", -1)])
def test_impossible_values_rejected(field, value):
    assert TestClient(main.app).post("/v1/score", json={**FEATURES, field: value}).status_code == 422
