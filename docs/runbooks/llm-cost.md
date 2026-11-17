# LLM spend high

**Alert:** `AISpendHigh`: estimated spend above 5 USD/hour for 30 minutes.

Estimates come from token counts × `AI_MODEL_PRICES`, so check that prices are current.

1. *Tokens per minute* by model: is one model dominating (fallback to a pricier vendor)?
2. Bulk jobs: `analysis_jobs_total` and `analysis_job_claims_total`. Large uploads with
   `auto_analyze` are the usual cause.
3. Cache effectiveness: `ai_cache_hits_total`. A drop after a deploy usually means the
   cache key changed (new prompt version or model chain), which is expected once.
4. Levers: lower `RATE_LIMIT_BULK_PER_MINUTE`, disable `AI_JUDGE_ENABLED` (one extra
   call per approval), set `AI_HEDGE_AFTER_S=0` (hedging duplicates calls), use a cheaper
   primary model, or reduce `AI_MAX_TOKENS_PER_RUN`.
