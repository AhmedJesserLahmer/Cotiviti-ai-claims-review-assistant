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
    model_version: str | None = None
    ood_flags: list[str] = Field(default_factory=list)
    # "live" = scored now by ml-service; "cache" = reused from the last analysis
    # because ml-service was unavailable (stale, never auto-approved).
    signals_source: Literal["live", "cache"] = "live"


class AnalysisRequest(BaseModel):
    claim_id: str = Field(min_length=1, max_length=64)
    # Skip the LLM result cache (explicit "re-run" from a reviewer).
    bypass_cache: bool = False


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
    """Features needed by the claim-level models (classification + payment prediction).

    Bounds reject physically impossible values outright (422); values that are
    possible but outside what the models were trained on are reported as
    ``ood_flags`` in the response instead.
    """

    billed_amount: float = Field(gt=0, le=10_000_000)
    length_of_stay: int = Field(default=0, ge=0, le=365)
    prior_claims_count: int = Field(default=0, ge=0, le=10_000)
    treatment_type: str = Field(min_length=1, max_length=40)
    procedure_code: str = Field(min_length=1, max_length=20)
    patient_age: int = Field(ge=0, le=120)
    provider_avg_claim_amount: float = Field(ge=0, le=10_000_000)


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
    # Reasons the input looks unlike the training data; predictions are less reliable.
    ood_flags: list[str] = Field(default_factory=list)
