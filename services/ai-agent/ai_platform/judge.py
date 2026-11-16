"""LLM-as-judge: an independent consistency audit of LLM approvals.

Only approvals are audited, because only approvals can cause harm automatically (a
wrongly flagged claim costs reviewer time; a wrongly approved one costs money). The
judge can only *add* a blocking policy violation, which escalates the approval to
manual review; it can never approve anything.
"""

from __future__ import annotations

import json

from ai_platform.audit import AIRunMetadata
from ai_platform.errors import AllProvidersFailedError, OutputValidationError, TokenBudgetExceededError
from ai_platform.guardrails.base import GuardrailFinding
from ai_platform.guardrails.policy import PolicyViolation
from ai_platform.prompts import CLAIM_JUDGE
from ai_platform.validation.schemas import JudgeOutput, RecommendationOutput
from ai_platform.validation.structured import generate_structured


async def audit_approval(
    client,
    *,
    output: RecommendationOutput,
    reasoning: str,
    signals: dict,
    run: AIRunMetadata,
    fail_closed: bool,
    max_tokens: int | None = None,
) -> list[PolicyViolation]:
    run.use_prompt(CLAIM_JUDGE.name, CLAIM_JUDGE.version)
    messages = CLAIM_JUDGE.render(
        decision_json=output.model_dump_json(),
        reasoning=reasoning,
        signals_json=json.dumps(signals, default=str),
    )
    try:
        verdict = await generate_structured(
            client, messages, JudgeOutput, max_repairs=1, recorder=run, counter=run, temperature=0.0,
            max_tokens=max_tokens,
        )
    except (AllProvidersFailedError, OutputValidationError, TokenBudgetExceededError) as exc:
        run.judge = {"consistent": None, "error": str(exc)[:200]}
        run.add_event(GuardrailFinding("llm_judge", "warned", f"judge unavailable: {str(exc)[:120]}"))
        if fail_closed:
            return [PolicyViolation("judge_unavailable", "block", "consistency audit could not run")]
        return []

    run.judge = verdict.model_dump()
    if verdict.consistent:
        return []
    issues = "; ".join(verdict.issues) or "decision inconsistent with reasoning"
    return [PolicyViolation("judge_inconsistent", "block", f"consistency audit failed: {issues}")]
