"""Model inference and dataset seeding endpoints (internal)."""

from fastapi import APIRouter
from prometheus_client import Counter

from claims_common.contracts import ClassifyResponse, PaymentResponse, ScoreRequest, ScoreResponse, SeedResponse
from data_gen.seed_mongo import seed
from ml.inference import active_version, classify_claim, ood_flags, predict_payment

router = APIRouter(prefix="/v1", tags=["scoring"])

PREDICTIONS = Counter("ml_predictions_total", "Model predictions served", ["endpoint", "model_version"])
OOD_INPUTS = Counter("ml_out_of_distribution_total", "Scored inputs flagged out of distribution", ["feature"])
RISK_LABELS = Counter("ml_predicted_risk_total", "Predicted risk labels", ["label"])


def _claim(body: ScoreRequest) -> dict:
    return body.model_dump(exclude={"patient_age", "provider_avg_claim_amount"})


def _ood(body: ScoreRequest) -> list[str]:
    features = body.model_dump()
    features["age"] = features.pop("patient_age")
    flags = ood_flags(features)
    for flag in flags:
        OOD_INPUTS.labels(flag.split("=")[0].replace("unknown ", "").split(" ")[0]).inc()
    return flags


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
    PREDICTIONS.labels("score", active_version()).inc()
    RISK_LABELS.labels(label).inc()
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
