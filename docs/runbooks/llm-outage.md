# LLM outage / degraded to rule engine

**Alerts:** `AIDegradedToRuleEngine` (>20% of decisions without an LLM, 15 min),
`AIDegradedToRuleEngineCritical` (>50%, 10 min), `AILLMLatencyHigh`.

**User impact:** analyses still complete. Decisions come from the deterministic rule engine;
the dashboard shows "Rule engine (AI unavailable)" and reasoning starts with
"[Automated rule-based reasoning]". The rule engine is conservative: more claims go to
manual review, so reviewer queues grow. Nothing is auto-denied.

## Confirm

1. Grafana "AI Reliability": *Fallbacks per minute* (`rule_engine` vs `model`) and
   *LLM attempt error ratio by model*.
2. Why runs degrade (the reason is in every audit trail):
   `kubectl -n $NS logs deploy/claims-review-ai-agent | grep '"degraded": true' | tail`
   or look at `ai_metadata.degraded_reason` of a recent analysis.
3. Circuit states: `kubectl -n $NS exec deploy/claims-review-claims-api -- python -c "import urllib.request;print(urllib.request.urlopen('http://claims-review-ai-agent:8002/health/ready').read())"`.

## Common causes and actions

| `degraded_reason` contains | Cause | Action |
|---|---|---|
| `AuthenticationError`, `401` | Key revoked or rotated | Update `GROQ_API_KEY` in the secret manager; External Secrets syncs within `refreshInterval`, then `kubectl -n $NS rollout restart deploy/claims-review-ai-agent` |
| `RateLimitError`, `429` | Account throttled | Lower load (bulk jobs), raise the provider quota, or enable the cross-vendor fallback (`AI_OPENAI_*`) |
| `timeout`, `503`, `APIConnectionError` | Provider incident | Check the provider status page. The circuit breaker stops the waste; nothing to do until recovery |
| `token budget` | Prompts/claims grew | Check `ai_llm_tokens_total`; raise `AI_MAX_TOKENS_PER_RUN` only after review |
| `disabled (no credentials or offline mode)` | Config | `AI_OFFLINE_MODE` set or key missing in the release Secret |
| `model output invalid` | Model regression | See [model-regression.md](model-regression.md) |

## Recovery

Circuits half-open after `AI_CIRCUIT_RECOVERY_S` (30 s) and close on the first success, so
recovery is automatic. Afterwards, re-analyze claims decided by the rules if needed:
`POST /jobs/analyses` with their ids (re-analysis bypasses nothing: guardrails still apply).
