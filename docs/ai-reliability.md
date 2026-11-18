# AI Reliability Layer

The LLM is one input to a claim decision, never the last word. This document explains
the layers that sit between the LangGraph agent and the model, what each one guarantees,
and how to operate them.

Code: `ai_platform/` (in the AI agent service), entry point `ClaimReviewAI`.

## Pipeline

```
claim + provider + ML signals
        │
        ▼
┌─────────────────────────┐   strips control chars, fence characters, caps length,
│ input guardrails        │   removes prompt-injection attempts, redacts PII
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐   name@version, untrusted data fenced in <claim_data>
│ versioned prompt        │
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐   per model: circuit breaker → hard timeout → retries with
│ resilient LLM client    │   backoff + jitter; then the next model in the chain
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐   reasoning: strip markup, redact echoed PII, reject prompt
│ output validation       │   leakage. decision: tolerant JSON → schema → repair re-prompt
└──────────┬──────────────┘
           ▼
┌─────────────────────────┐   re-derives red flags from ML signals; may only escalate
│ policy guardrail        │   towards manual review, never approve or deny
└──────────┬──────────────┘
           ▼
     decision + AIRunMetadata (audit trail)
```

If any LLM step cannot produce a valid answer, the **rule engine** (`fallback/rules.py`)
produces the reasoning and decision instead and the run is marked `degraded`. An
analysis request therefore never fails because of the LLM.

## Guarantees

| Failure | Behaviour |
|---|---|
| Model slow | Hard timeout (`AI_REQUEST_TIMEOUT_S`), then retry |
| 429 / 5xx / connection reset | Retried with capped exponential backoff and full jitter, `retry-after` respected |
| Bad key / unknown model | Not retried; next model in the chain |
| Model down repeatedly | Circuit opens after `AI_CIRCUIT_FAILURE_THRESHOLD` failures and is skipped instantly for `AI_CIRCUIT_RECOVERY_S` |
| All models down / no key | Deterministic rule engine, `decision_source = "rules"` |
| Prose instead of JSON | Tolerant extraction (fences, trailing commas, smart quotes), then up to `AI_MAX_REPAIR_ATTEMPTS` repair prompts |
| Out-of-vocabulary decision | Schema rejects it and triggers a repair |
| Injected instructions in CSV fields | Field removed, run flagged, approval blocked by policy |
| PII in input or output | Redacted before sending and before storing |
| Model approves a risky claim | Policy escalates it to `flag_for_review` and records the override |
| Agent asks for more data again and again | Data budget enforced, even with policy disabled |

## The policy invariant

`guardrails/policy.py` encodes one rule: **guardrails can only make a decision more
conservative.** An approval is escalated when any blocking red flag is present:

- `high_risk`: predicted label High, or P(High) ≥ `AI_HIGH_RISK_PROBABILITY_THRESHOLD`
- `recent_anomaly`: the provider's most recent billing day is anomalous
- `billing_gap`: billed amount > `AI_BILLING_RATIO_THRESHOLD` × predicted payment
- `untrusted_input`: a prompt-injection attempt was removed from the claim

`outlier_provider` and `anomaly_history` are warnings: they are recorded but do not
override. Nothing ever auto-denies a claim; denial stays a human decision.

## Audit trail

Every analysis stores `ai_metadata` next to the decision:

- `prompt_versions`: exact prompts used
- `attempts[]`: provider, model, attempt number, outcome, latency, error
- `model_used`, `model_fallback_used`, `degraded`, `degraded_reason`, `decision_source`
- `repair_attempts`, `guardrail_events[]`, `injection_detected`
- `recommendation_overridden`, `original_recommendation`, `policy_violations[]`
- `confidence`, `key_factors[]`, `total_latency_ms`

The dashboard renders it in the **AI Reliability** panel, and each decision is also
logged as one structured JSON line (`claims_api.agent` logger).

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | – | Groq credentials; without it the rule engine is used |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Primary model |
| `AI_FALLBACK_MODELS` | `qwen/qwen3.8-27b,openai/gpt-oss-20b` | Comma-separated fallback chain (a different model family first, so one family's outage or retirement does not take out the whole chain) |
| `AI_OFFLINE_MODE` | `false` | Force the rule engine (demos, CI, outage drills) |
| `AI_REQUEST_TIMEOUT_S` | `20` | Hard deadline per call |
| `AI_MAX_RETRIES` | `2` | Retries per model (attempts = retries + 1) |
| `AI_BACKOFF_BASE_S` / `AI_BACKOFF_MAX_S` | `0.5` / `8` | Backoff curve |
| `AI_CIRCUIT_FAILURE_THRESHOLD` | `5` | Failures before a circuit opens |
| `AI_CIRCUIT_RECOVERY_S` | `30` | Time before a trial call |
| `AI_MAX_REPAIR_ATTEMPTS` | `1` | JSON repair re-prompts |
| `AI_GUARDRAILS_ENABLED` | `true` | Input sanitization and output checks |
| `AI_PII_REDACTION_ENABLED` | `true` | PII redaction |
| `AI_POLICY_ENFORCEMENT_ENABLED` | `true` | Policy guardrail |
| `AI_HIGH_RISK_PROBABILITY_THRESHOLD` | `0.6` | Policy `high_risk` threshold |
| `AI_BILLING_RATIO_THRESHOLD` | `2.5` | Policy `billing_gap` threshold |

## Testing

`tests/ai/` covers every layer with `ScriptedProvider`, which replays completions
and errors deterministically (no network, no key). Run them with `make test-ai`.

## Operating it

- **Outage drill:** set `AI_OFFLINE_MODE=true`. The dashboard shows "Rule engine (AI unavailable)".
- **Circuit states:** `GET /health/ready` → `ai.circuits`.
- **Changing a prompt:** edit it in `prompts.py` *and bump its version*; old analyses keep the old version id.
