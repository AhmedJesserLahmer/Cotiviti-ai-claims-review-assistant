from ai_platform.audit import AIRunMetadata
from ai_platform.guardrails.base import GuardrailFinding


def test_records_attempts_and_detects_model_fallback():
    run = AIRunMetadata()
    run.record_attempt(provider="groq", model="big", attempt=1, outcome="error", latency_ms=5, error="timeout")
    run.record_attempt(provider="groq", model="small", attempt=1, outcome="success", latency_ms=3)
    assert run.model_used == "small" and run.model_fallback_used
    assert [a.outcome for a in run.attempts] == ["error", "success"]


def test_primary_success_is_not_a_fallback():
    run = AIRunMetadata()
    run.record_attempt(provider="groq", model="big", attempt=1, outcome="success", latency_ms=3)
    assert not run.model_fallback_used


def test_guardrail_events_and_injection_flag():
    run = AIRunMetadata()
    run.add_events([GuardrailFinding("pii", "redacted", "x"), GuardrailFinding("prompt_injection", "blocked", "y")])
    assert run.injection_detected and len(run.guardrail_events) == 2


def test_repairs_degradation_and_serialization():
    run = AIRunMetadata()
    run.record_repair("bad json")
    run.mark_degraded("all providers failed")
    run.mark_degraded("second reason is ignored")
    run.use_prompt("claim_reasoning", "2.0.0")
    data = run.finish().model_dump()
    assert data["repair_attempts"] == 1 and data["decision_source"] == "rules"
    assert data["degraded_reason"] == "all providers failed"
    assert data["prompt_versions"] == {"claim_reasoning": "2.0.0"}
    assert data["total_latency_ms"] >= 0
    assert "_t0" not in data
