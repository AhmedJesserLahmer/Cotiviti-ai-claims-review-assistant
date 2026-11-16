from pydantic import BaseModel

from claims_common.contracts import AnalysisResult, MLSignals, SeedResponse


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


class ClaimUploadError(BaseModel):
    row: int
    reason: str


class ClaimUploadResponse(BaseModel):
    inserted_count: int
    claim_ids: list[str]
    errors: list[ClaimUploadError]
    analyses: list[AnalysisResult] | None = None
    analysis_errors: list[ClaimUploadError] | None = None


__all__ = [
    "AnalysisResult", "ClaimOut", "ClaimUploadError", "ClaimUploadResponse", "MLSignals",
    "ProviderClusterOut", "SeedResponse", "TimeseriesPoint",
]
