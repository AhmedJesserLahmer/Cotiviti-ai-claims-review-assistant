"""Prometheus metrics for the AI layer, recorded once per finished analysis.

Recording from the final AIRunMetadata keeps a single source of truth: the numbers
on dashboards are exactly what the audit trail says happened.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

LLM_ATTEMPTS = Counter("ai_llm_attempts_total", "LLM call attempts", ["provider", "model", "outcome"])
LLM_LATENCY = Histogram(
    "ai_llm_attempt_duration_seconds", "LLM call latency per attempt", ["provider", "model"],
    buckets=(0.25, 0.5, 1, 2, 4, 8, 15, 30, 60),
)
LLM_TOKENS = Counter("ai_llm_tokens_total", "LLM tokens consumed", ["model", "kind"])
LLM_COST = Counter("ai_llm_estimated_cost_usd_total", "Estimated LLM spend in USD", ["model"])
DECISIONS = Counter("ai_decisions_total", "Final claim decisions", ["recommendation", "source"])
FALLBACKS = Counter("ai_fallbacks_total", "Degradations", ["kind"])
GUARDRAIL_EVENTS = Counter("ai_guardrail_events_total", "Guardrail events", ["guardrail", "action"])
POLICY_OVERRIDES = Counter("ai_policy_overrides_total", "Decisions escalated by policy", ["original"])
CACHE_HITS = Counter("ai_cache_hits_total", "LLM results served from cache", ["prompt"])
ANALYSIS_LATENCY = Histogram(
    "ai_analysis_duration_seconds", "End-to-end analysis latency", ["source"],
    buckets=(0.5, 1, 2, 4, 8, 15, 30, 60, 120),
)
CIRCUIT_STATE = Gauge("ai_circuit_state", "Circuit breaker state (0 closed, 1 half-open, 2 open)", ["breaker"])

_STATE_VALUE = {"closed": 0, "half_open": 1, "open": 2}


def record_run(run, recommendation: str, circuits: list[dict] | None = None) -> None:
    for attempt in run.attempts:
        LLM_ATTEMPTS.labels(attempt.provider, attempt.model, attempt.outcome).inc()
        if attempt.outcome != "circuit_open":
            LLM_LATENCY.labels(attempt.provider, attempt.model).observe(attempt.latency_ms / 1000)
    model = run.model_used or "none"
    if run.prompt_tokens or run.completion_tokens:
        LLM_TOKENS.labels(model, "prompt").inc(run.prompt_tokens)
        LLM_TOKENS.labels(model, "completion").inc(run.completion_tokens)
        LLM_COST.labels(model).inc(run.estimated_cost_usd)
    DECISIONS.labels(recommendation, run.decision_source).inc()
    if run.degraded:
        FALLBACKS.labels("rule_engine").inc()
    if run.model_fallback_used:
        FALLBACKS.labels("model").inc()
    for event in run.guardrail_events:
        GUARDRAIL_EVENTS.labels(event.guardrail, event.action).inc()
        if event.guardrail == "ml_fallback":
            FALLBACKS.labels("ml_cache").inc()
    if run.recommendation_overridden:
        POLICY_OVERRIDES.labels(run.original_recommendation or "unknown").inc()
    for prompt in run.cache_hits:
        CACHE_HITS.labels(prompt).inc()
    if run.total_latency_ms is not None:
        ANALYSIS_LATENCY.labels(run.decision_source).observe(run.total_latency_ms / 1000)
    for circuit in circuits or []:
        CIRCUIT_STATE.labels(circuit["name"]).set(_STATE_VALUE.get(circuit["state"], 0))
