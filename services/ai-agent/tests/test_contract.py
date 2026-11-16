"""ai-agent output satisfies the contract claims-api consumes, including real audit metadata."""

import pytest

pytest.importorskip("langgraph")

from ai_platform.audit import AIRunMetadata  # noqa: E402
from claims_common.contracts import AnalysisResult  # noqa: E402


def test_audit_metadata_round_trips_through_the_contract():
    run = AIRunMetadata()
    run.record_attempt(provider="groq", model="m", attempt=1, outcome="success", latency_ms=12.0)
    run.use_prompt("claim_reasoning", "2.0.0")
    result = AnalysisResult.model_validate({
        "claim_id": "C1",
        "signals": {
            "predicted_risk_label": "Low", "risk_probabilities": {"Low": 1.0}, "predicted_paid_amount": 1.0,
            "provider_cluster_id": 0, "provider_cluster_label": "x", "anomaly_flagged_days": 0,
            "anomaly_recent_score": 0.1, "is_recent_anomaly": False, "model_version": "v1", "ood_flags": [],
        },
        "reasoning": "r", "recommendation": "approve", "recommendation_summary": "s", "loops": 0,
        "ai_metadata": run.finish().model_dump(),
    })
    dumped = result.model_dump()
    assert dumped["ai_metadata"]["model_used"] == "m"
    assert dumped["signals"]["model_version"] == "v1"
    # The frontend's AIMetadata type relies on these keys.
    for key in ["decision_source", "attempts", "guardrail_events", "recommendation_overridden", "prompt_versions"]:
        assert key in dumped["ai_metadata"]
