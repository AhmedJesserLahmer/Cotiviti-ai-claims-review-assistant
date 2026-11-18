# 0003: Degrade to a deterministic rule engine instead of failing

**Context.** The POC returned HTTP 500 whenever Groq was unavailable or the key missing,
so an LLM outage stopped claims review entirely.

**Decision.** If every model in the chain fails, the budget is spent, or the output stays
invalid after repairs, the rule engine (`fallback/rules.py`) produces reasoning and a
decision from the same red flags the policy uses. The run is marked `degraded` with the
reason, shown in the dashboard and counted in metrics.

**Consequences.** Analyses always complete; the degraded path is at least as conservative
as the LLM path. The rule engine's accuracy floor is measured by `run_eval --mode rules`.
