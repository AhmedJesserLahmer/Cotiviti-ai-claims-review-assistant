from typing import Any, Literal

from pydantic import BaseModel


class ClaimOut(BaseModel):
    claim_id: str
    provider_id: str
    patient_id: str
    procedure_code: str
    diagnosis_code: str
    treatment_type: str
    billed_amount: float
    paid_amount: float
    claim_date: str
    length_of_stay: int
    prior_claims_count: int
    status: str
    risk_label: str


class MLSignals(BaseModel):
    predicted_risk_label: str
    risk_probabilities: dict[str, float]
    predicted_paid_amount: float
    provider_cluster_id: int
    provider_cluster_label: str
    anomaly_flagged_days: int
    anomaly_recent_score: float
    is_recent_anomaly: bool


class AnalysisResult(BaseModel):
    claim_id: str
    signals: MLSignals
    reasoning: str
    recommendation: Literal["approve", "flag_for_review", "request_more_data"]
    recommendation_summary: str
    loops: int


class TimeseriesPoint(BaseModel):
    date: str
    daily_claim_count: int
    daily_paid_total: float
    anomaly_score: float
    is_anomaly: bool


class ProviderClusterOut(BaseModel):
    provider_id: str
    cluster_id: int
    cluster_label: str
    avg_billed: float
    claim_volume: int
    denial_rate: float
    avg_length_of_stay: float


class SeedResponse(BaseModel):
    status: str
    counts: dict[str, int]


class ClaimUploadError(BaseModel):
    row: int
    reason: str


class ClaimUploadResponse(BaseModel):
    inserted_count: int
    claim_ids: list[str]
    errors: list[ClaimUploadError]
    analyses: list[AnalysisResult] | None = None
    analysis_errors: list[ClaimUploadError] | None = None
