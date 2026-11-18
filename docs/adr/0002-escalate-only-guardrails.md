# 0002: The LLM never has the last word; guardrails only escalate

**Context.** An LLM can be wrong, manipulated through claim fields, or inconsistent with
the ML models. In claims review the costly error is an automatic approval of a bad claim.

**Decision.** Every decision passes deterministic checks after the model (policy red flags
from ML signals, grounding of cited numbers, calibrated confidence, optional LLM judge).
They may only move a decision towards `flag_for_review`. Nothing automated ever denies a
claim; denial is a human decision.

**Consequences.** Unsafe approvals are bounded by deterministic code that is unit-tested
and evaluated (`evals/`, zero unsafe approvals is a CI gate). More claims reach reviewers
when the model is weak; that is visible (`AIPolicyOverrideSpike`) and accepted.
