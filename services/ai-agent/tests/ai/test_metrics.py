from prometheus_client import REGISTRY

from ai_platform.audit import AIRunMetadata
from ai_platform.guardrails.base import GuardrailFinding
from ai_platform.metrics import record_run


def value(name, labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_record_run_reflects_the_audit_trail():
    run = AIRunMetadata()
    run.record_attempt(provider="groq", model="metrics-big", attempt=1, outcome="error", latency_ms=1200, error="t")
    run.record_attempt(provider="groq", model="metrics-small", attempt=1, outcome="success", latency_ms=300)
    run.set_prices({"metrics-small": (1.0, 1.0)})
    run.record_usage(model="metrics-small", prompt_tokens=1000, completion_tokens=500)
    run.add_event(GuardrailFinding("prompt_injection", "blocked", "x"))
    run.recommendation_overridden, run.original_recommendation = True, "approve"
    run.finish()

    before = value("ai_decisions_total", {"recommendation": "flag_for_review", "source": "llm"})
    record_run(run, "flag_for_review", [{"name": "groq/metrics-big", "state": "open"}])
    assert value("ai_decisions_total", {"recommendation": "flag_for_review", "source": "llm"}) == before + 1
    assert value("ai_llm_attempts_total", {"provider": "groq", "model": "metrics-big", "outcome": "error"}) >= 1
    assert value("ai_fallbacks_total", {"kind": "model"}) >= 1
    assert value("ai_llm_tokens_total", {"model": "metrics-small", "kind": "completion"}) >= 500
    assert value("ai_guardrail_events_total", {"guardrail": "prompt_injection", "action": "blocked"}) >= 1
    assert value("ai_policy_overrides_total", {"original": "approve"}) >= 1
    assert value("ai_circuit_state", {"breaker": "groq/metrics-big"}) == 2
