"""ml-service responses satisfy the contract ai-agent consumes."""

import pytest

pytest.importorskip("sklearn")

from ml import registry  # noqa: E402

try:
    registry.current_version()
except registry.ModelNotFoundError:
    pytest.skip("models not trained yet", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from claims_common.contracts import ClassifyResponse, PaymentResponse, ScoreRequest, ScoreResponse  # noqa: E402

REQUEST = ScoreRequest(
    billed_amount=1200.0, length_of_stay=1, prior_claims_count=0, treatment_type="Outpatient",
    procedure_code="CPT10003", patient_age=45, provider_avg_claim_amount=1100.0,
).model_dump()


@pytest.mark.parametrize(
    "path, model", [("/v1/score", ScoreResponse), ("/v1/classify", ClassifyResponse), ("/v1/predict-payment", PaymentResponse)]
)
def test_responses_match_shared_contract(path, model):
    response = TestClient(main.app).post(path, json=REQUEST)
    assert response.status_code == 200
    parsed = model.model_validate(response.json())
    assert parsed.model_version == registry.current_version()


def test_openapi_publishes_the_shared_schema():
    schemas = TestClient(main.app).get("/openapi.json").json()["components"]["schemas"]
    assert set(ScoreResponse.model_fields) <= set(schemas["ScoreResponse"]["properties"])
