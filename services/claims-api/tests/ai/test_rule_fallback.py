from ai_platform.fallback import rules

CLAIM = {"billed_amount": 1000.0}
LOW = {
    "predicted_risk_label": "Low",
    "risk_probabilities": {"Low": 0.8, "High": 0.05},
    "predicted_paid_amount": 900.0,
    "provider_cluster_label": "Standard Volume Care",
    "anomaly_flagged_days": 1,
    "anomaly_recent_score": 0.4,
    "is_recent_anomaly": False,
}


def test_routine_claim_is_approved():
    out = rules.recommend(CLAIM, LOW)
    assert out.recommendation == "approve"
    assert out.confidence < 0.7


def test_red_flag_is_flagged_with_reason():
    out = rules.recommend(CLAIM, {**LOW, "is_recent_anomaly": True})
    assert out.recommendation == "flag_for_review"
    assert "recent_anomaly" in out.key_factors


def test_medium_risk_or_high_amount_goes_to_human():
    assert rules.recommend(CLAIM, {**LOW, "predicted_risk_label": "Medium"}).recommendation == "flag_for_review"
    assert rules.recommend({"billed_amount": 2000.0}, LOW).recommendation == "flag_for_review"
    assert rules.recommend(CLAIM, {**LOW, "predicted_paid_amount": 0}).recommendation == "flag_for_review"


def test_injection_is_never_approved():
    assert rules.recommend(CLAIM, LOW, injection_detected=True).recommendation == "flag_for_review"


def test_rules_never_request_more_data_or_deny():
    variants = [LOW, {**LOW, "predicted_risk_label": "High"}, {**LOW, "is_recent_anomaly": True}, {}]
    assert {rules.recommend(CLAIM, s).recommendation for s in variants} <= {"approve", "flag_for_review"}


def test_reasoning_is_explicit_about_degradation():
    text = rules.build_reasoning(CLAIM, LOW)
    assert text.startswith("[Automated rule-based reasoning")
    assert "1.11x" in text and "Standard Volume Care" in text
    assert rules.build_reasoning({}, {})  # never crashes on missing data
