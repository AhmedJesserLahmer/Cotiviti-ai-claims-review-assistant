# 0006: Cache validated LLM results at the facade, not raw completions

**Context.** Re-analyzing an unchanged claim should not cost tokens. Caching raw model text
would also cache malformed or unsafe outputs.

**Decision.** `ClaimReviewAI` caches only sanitized reasoning and schema-valid
recommendation JSON, keyed by prompt version, model chain and the exact rendered
messages. Policy, grounding, calibration and the judge are re-applied on every run.
A reviewer's "Re-run" bypasses the cache.

**Consequences.** Cached decisions still pass today's guardrails; a prompt or model change
naturally misses the cache. Identical inputs return identical decisions within the TTL,
which is the desired behaviour for audits.
