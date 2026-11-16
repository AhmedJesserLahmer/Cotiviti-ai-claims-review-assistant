"""Confidence calibration for recommendations.

The LLM's self-reported confidence is uncalibrated (models say 0.9 for almost
everything). The calibrated score blends it with independent evidence, the ML
classifier's support for the same decision, and discounts it when the inputs are
known to be weak:

    calibrated = w * llm_confidence + (1 - w) * ml_support
    x 0.8 if the ML input was out of distribution
    x 0.8 if the ML signals were reused from cache (stale)
    capped at 0.6 when the decision came from the rule engine

``ml_support`` is P(Low) + P(Medium)/2 for an approval and P(High) + P(Medium)/2 for
a flag (how much the classifier agrees). An approval whose calibrated confidence is
below ``AI_MIN_APPROVE_CONFIDENCE`` abstains: it goes to a human instead.
"""

from __future__ import annotations

DEFAULT_LLM_CONFIDENCE = 0.5
LLM_WEIGHT = 0.5
RULES_CAP = 0.6


def ml_support(recommendation: str, probabilities: dict[str, float]) -> float:
    low, medium, high = (float(probabilities.get(k, 0.0)) for k in ("Low", "Medium", "High"))
    if recommendation == "approve":
        return low + medium / 2
    if recommendation == "flag_for_review":
        return high + medium / 2
    return 0.5


def calibrate(
    recommendation: str,
    llm_confidence: float | None,
    signals: dict,
    *,
    from_rules: bool,
) -> float:
    llm = DEFAULT_LLM_CONFIDENCE if llm_confidence is None else float(llm_confidence)
    score = LLM_WEIGHT * llm + (1 - LLM_WEIGHT) * ml_support(recommendation, signals.get("risk_probabilities") or {})
    if signals.get("ood_flags"):
        score *= 0.8
    if signals.get("signals_source") == "cache":
        score *= 0.8
    if from_rules:
        score = min(score, RULES_CAP)
    return round(max(0.0, min(1.0, score)), 3)
