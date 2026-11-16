"""Production AI layer for the Claims Review Assistant.

This package wraps every LLM interaction with:

* resilience  - timeouts, retries with backoff, circuit breakers, model fallbacks
* validation  - tolerant JSON parsing, schema validation, repair re-prompts
* guardrails  - PII redaction, prompt-injection filtering, output sanitization,
                and a policy layer that cross-checks the LLM against ML signals
* fallback    - a deterministic rule engine used when no LLM is available
* audit       - per-run metadata describing exactly what happened

It depends only on the shared claims_common library, never on the rest of the
service, so it can move between services unchanged.
"""
