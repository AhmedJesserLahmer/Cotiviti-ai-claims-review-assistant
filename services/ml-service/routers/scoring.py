"""Model inference and dataset seeding endpoints (internal)."""

from fastapi import APIRouter

from claims_common.contracts import ClassifyResponse, PaymentResponse, ScoreRequest, ScoreResponse, SeedResponse
from data_gen.seed_mongo import seed
from ml.inference import active_version, classify_claim, ood_flags, predict_payment

router = APIRouter(prefix="/v1", tags=["scoring"])


def _claim(body: ScoreRequest) -> dict:
    return body.model_dump(exclude={"patient_age", "provider_avg_claim_amount"})


def _ood(body: ScoreRequest) -> list[str]:
    features = body.model_dump()
    features["age"] = features.pop("patient_age")
    return ood_flags(features)


@router.post("/classify", response_model=ClassifyResponse)
async def classify(body: ScoreRequest):
    label, probabilities = classify_claim(_claim(body), {"age": body.patient_age})
    return ClassifyResponse(
        predicted_risk_label=label, risk_probabilities=probabilities, model_version=active_version()
    )


@router.post("/predict-payment", response_model=PaymentResponse)
async def predict(body: ScoreRequest):
    return PaymentResponse(
        predicted_paid_amount=predict_payment(_claim(body), body.provider_avg_claim_amount),
        model_version=active_version(),
    )


@router.post("/score", response_model=ScoreResponse)
async def score(body: ScoreRequest):
    """Both claim-level models in one round trip (what the agent uses)."""
    claim = _claim(body)
    label, probabilities = classify_claim(claim, {"age": body.patient_age})
    return ScoreResponse(
        predicted_risk_label=label,
        risk_probabilities=probabilities,
        predicted_paid_amount=predict_payment(claim, body.provider_avg_claim_amount),
        model_version=active_version(),
        ood_flags=_ood(body),
    )


@router.post("/seed", response_model=SeedResponse)
async def seed_database():
    return SeedResponse(status="ok", counts=await seed())
