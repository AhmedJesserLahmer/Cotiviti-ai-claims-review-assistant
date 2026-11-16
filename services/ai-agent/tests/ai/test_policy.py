import pytest

from ai_platform.guardrails.policy import PolicyThresholds, enforce_policy, evaluate_signals
from ai_platform.validation.schemas import RecommendationOutput

CLAIM = {"billed_amount": 1000.0}
CLEAN = {
    "predicted_risk_label": "Low",
    "risk_probabilities": {"Low": 0.8, "Medium": 0.15, "High": 0.05},
    "predicted_paid_amount": 900.0,
    "provider_cluster_label": "Standard Volume Care",
    "anomaly_flagged_days": 0,
    "anomaly_recent_score": 0.4,
    "is_recent_anomaly": False,
}


def out(rec):
    return RecommendationOutput(recommendation=rec, summary="model says so", key_factors=["x"])


def test_clean_claim_approval_is_kept():
    decision = enforce_policy(out("approve"), CLAIM, CLEAN)
    assert decision.output.recommendation == "approve"
    assert not decision.overridden and decision.violations == []


@pytest.mark.parametrize(
    "change, rule",
    [
        ({"predicted_risk_label": "High"}, "high_risk"),
        ({"risk_probabilities": {"High": 0.7}}, "high_risk"),
        ({"is_recent_anomaly": True}, "recent_anomaly"),
        ({"predicted_paid_amount": 100.0}, "billing_gap"),
        ({"ood_flags": ["unknown treatment_type 'X'"]}, "ml_out_of_distribution"),
    ],
)
def test_blocking_rules_escalate_approvals(change, rule):
    decision = enforce_policy(out("approve"), CLAIM, {**CLEAN, **change})
    assert decision.output.recommendation == "flag_for_review"
    assert decision.overridden and decision.original_recommendation == "approve"
    assert decision.output.key_factors[0] == rule
    assert "Escalated to manual review" in decision.output.summary


def test_injection_blocks_approval():
    decision = enforce_policy(out("approve"), CLAIM, CLEAN, injection_detected=True)
    assert decision.output.recommendation == "flag_for_review"


def test_warnings_never_override():
    signals = {**CLEAN, "provider_cluster_label": "High-Risk / High-Denial Outlier", "anomaly_flagged_days": 9}
    decision = enforce_policy(out("approve"), CLAIM, signals)
    assert decision.output.recommendation == "approve"
    assert {v.rule for v in decision.violations} == {"outlier_provider", "anomaly_history"}


def test_policy_never_relaxes_a_flag():
    decision = enforce_policy(out("flag_for_review"), CLAIM, {**CLEAN, "predicted_risk_label": "High"})
    assert decision.output.recommendation == "flag_for_review"
    assert not decision.overridden


def test_request_more_data_respects_budget():
    assert enforce_policy(out("request_more_data"), CLAIM, CLEAN).output.recommendation == "request_more_data"
    decision = enforce_policy(out("request_more_data"), CLAIM, CLEAN, allow_more_data=False)
    assert decision.output.recommendation == "flag_for_review"
    assert decision.violations[-1].rule == "data_budget"


def test_thresholds_are_configurable():
    lenient = PolicyThresholds(high_risk_probability=0.9, billing_ratio=20)
    assert evaluate_signals(CLAIM, {**CLEAN, "risk_probabilities": {"High": 0.7}, "predicted_paid_amount": 100}, lenient) == []
