export interface Claim {
  claim_id: string;
  provider_id: string;
  patient_id: string;
  procedure_code: string;
  diagnosis_code: string;
  treatment_type: string;
  billed_amount: number;
  paid_amount: number;
  claim_date: string;
  length_of_stay: number;
  prior_claims_count: number;
  status: string;
  risk_label: string;
}

export interface MLSignals {
  predicted_risk_label: string;
  risk_probabilities: Record<string, number>;
  predicted_paid_amount: number;
  provider_cluster_id: number;
  provider_cluster_label: string;
  anomaly_flagged_days: number;
  anomaly_recent_score: number;
  is_recent_anomaly: boolean;
}

export interface AnalysisResult {
  claim_id: string;
  signals: MLSignals;
  reasoning: string;
  recommendation: "approve" | "flag_for_review" | "request_more_data";
  recommendation_summary: string;
  loops: number;
}

export interface Provider {
  provider_id: string;
  name: string;
  specialty: string;
  region: string;
  avg_claim_amount: number;
  risk_baseline: number;
  avg_billed: number;
  claim_volume: number;
  denial_rate: number;
  avg_length_of_stay: number;
  cluster_id: number;
  cluster_label: string;
}

export interface TimeseriesPoint {
  date: string;
  daily_claim_count: number;
  daily_paid_total: number;
  anomaly_score: number;
  is_anomaly: boolean;
}

export interface ClaimUploadError {
  row: number;
  reason: string;
}

export interface ClaimUploadResponse {
  inserted_count: number;
  claim_ids: string[];
  errors: ClaimUploadError[];
  analyses: AnalysisResult[] | null;
  analysis_errors: ClaimUploadError[] | null;
}
