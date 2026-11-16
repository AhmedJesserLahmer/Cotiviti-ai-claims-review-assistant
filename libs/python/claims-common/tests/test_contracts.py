"""Backwards-compatibility guard for the wire contracts between services.

Services are deployed independently (rolling updates), so for a while an old
consumer talks to a new producer and vice versa. Adding a *required* field or
removing a field breaks that. This snapshot makes such a change fail loudly: update
it only together with a coordinated rollout plan.
"""

import pytest

from claims_common import contracts

REQUIRED_FIELDS = {
    "MLSignals": {
        "predicted_risk_label", "risk_probabilities", "predicted_paid_amount", "provider_cluster_id",
        "provider_cluster_label", "anomaly_flagged_days", "anomaly_recent_score", "is_recent_anomaly",
    },
    "AnalysisRequest": {"claim_id"},
    "AnalysisResult": {"claim_id", "signals", "reasoning", "recommendation", "recommendation_summary", "loops"},
    "ScoreRequest": {"billed_amount", "treatment_type", "procedure_code", "patient_age", "provider_avg_claim_amount"},
    "ScoreResponse": {"predicted_risk_label", "risk_probabilities", "predicted_paid_amount"},
    "ClassifyResponse": {"predicted_risk_label", "risk_probabilities"},
    "PaymentResponse": {"predicted_paid_amount"},
    "SeedResponse": {"status", "counts"},
}


@pytest.mark.parametrize("name", sorted(REQUIRED_FIELDS))
def test_required_fields_are_stable(name):
    model = getattr(contracts, name)
    required = {field for field, info in model.model_fields.items() if info.is_required()}
    assert required == REQUIRED_FIELDS[name], (
        f"{name} required fields changed; new fields must be optional for rolling deploys"
    )


def test_unknown_fields_from_newer_producers_are_ignored():
    signals = contracts.MLSignals.model_validate({
        "predicted_risk_label": "Low", "risk_probabilities": {}, "predicted_paid_amount": 1, "provider_cluster_id": 0,
        "provider_cluster_label": "x", "anomaly_flagged_days": 0, "anomaly_recent_score": 0, "is_recent_anomaly": False,
        "field_added_in_v2": 123,
    })
    assert signals.ood_flags == []
