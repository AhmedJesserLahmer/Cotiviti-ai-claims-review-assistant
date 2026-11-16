"""API contracts shared between services.

These models are the wire format between claims-api, ai-agent and ml-service. Changing
a field here is an API change: keep additions optional so older services keep working
during rolling deploys.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Recommendation = Literal["approve", "flag_for_review", "request_more_data"]


class MLSignals(BaseModel):
    predicted_risk_label: str
    risk_probabilities: dict[str, float]
    predicted_paid_amount: float
    provider_cluster_id: int
    provider_cluster_label: str
    anomaly_flagged_days: int
    anomaly_recent_score: float
    is_recent_anomaly: bool


class AnalysisRequest(BaseModel):
    claim_id: str = Field(min_length=1, max_length=64)


class AnalysisResult(BaseModel):
    claim_id: str
    signals: MLSignals
    reasoning: str
    recommendation: Recommendation
    recommendation_summary: str
    loops: int
    # AI audit trail (see ai_platform.audit.AIRunMetadata in ai-agent). Optional so
    # analyses stored before the AI reliability layer still validate.
    ai_metadata: dict[str, Any] | None = None


class SeedResponse(BaseModel):
    status: str
    counts: dict[str, int]


class ScoreRequest(BaseModel):
    """Features needed by the claim-level models (classification + payment prediction)."""

    billed_amount: float
    length_of_stay: int = 0
    prior_claims_count: int = 0
    treatment_type: str
    procedure_code: str
    patient_age: int
    provider_avg_claim_amount: float


class ClassifyResponse(BaseModel):
    predicted_risk_label: str
    risk_probabilities: dict[str, float]
    model_version: str | None = None


class PaymentResponse(BaseModel):
    predicted_paid_amount: float
    model_version: str | None = None


class ScoreResponse(BaseModel):
    predicted_risk_label: str
    risk_probabilities: dict[str, float]
    predicted_paid_amount: float
    model_version: str | None = None
