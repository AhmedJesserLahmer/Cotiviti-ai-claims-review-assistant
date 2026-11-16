"""Production AI layer for the Claims Review Assistant.

This package wraps every LLM interaction with:

* resilience  - timeouts, retries with backoff, circuit breakers, model fallbacks
* validation  - tolerant JSON parsing, schema validation, repair re-prompts
* guardrails  - PII redaction, prompt-injection filtering, output sanitization,
                and a policy layer that cross-checks the LLM against ML signals
* fallback    - a deterministic rule engine used when no LLM is available
* audit       - per-run metadata describing exactly what happened

It does not import anything from the rest of the service, so it can later be
moved into its own microservice (services/ai-agent) unchanged.
"""
