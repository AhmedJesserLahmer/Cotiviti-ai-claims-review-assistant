"""Rule-based reasoning and recommendation.

Used when every LLM provider is down, credentials are missing, offline mode is on, or
the model keeps returning invalid output. It reuses the policy red flags so the
degraded path is at least as conservative as the LLM path:

* any blocking red flag            -> flag_for_review
* Low risk, no anomaly, billed amount within 1.5x of predicted payment -> approve
* everything else                  -> flag_for_review

It never requests more data and never denies. Confidence is deliberately modest:
these are heuristics, and the response is marked as degraded so the UI can say so.
"""

from __future__ import annotations

from typing import Any

from ai_platform.guardrails.policy import PolicyThresholds, evaluate_signals
from ai_platform.validation.schemas import RecommendationOutput

SAFE_APPROVAL_RATIO = 1.5
ENGINE_NAME = "rules-v1"


def _ratio(claim: dict[str, Any], signals: dict[str, Any]) -> float | None:
    predicted = float(signals.get("predicted_paid_amount") or 0.0)
    if predicted <= 0:
        return None
    return float(claim.get("billed_amount") or 0.0) / predicted


def build_reasoning(claim: dict[str, Any], signals: dict[str, Any]) -> str:
    probabilities = signals.get("risk_probabilities") or {}
    probs = ", ".join(f"{k} {float(v):.0%}" for k, v in probabilities.items()) or "n/a"
    ratio = _ratio(claim, signals)
    ratio_text = f"{ratio:.2f}x the predicted payment" if ratio is not None else "no payment prediction available"
    anomaly = (
        f"the most recent day is anomalous (score {float(signals.get('anomaly_recent_score', 0)):.2f})"
        if signals.get("is_recent_anomaly")
        else "the most recent day looks normal"
    )
    return "\n".join([
        "[Automated rule-based reasoning: the AI model was unavailable.]",
        f"1. Treatment risk: the classifier predicts {signals.get('predicted_risk_label', 'Unknown')} "
        f"risk ({probs}).",
        f"2. Payment: billed ${float(claim.get('billed_amount') or 0):,.2f}, which is {ratio_text} "
        f"(${float(signals.get('predicted_paid_amount') or 0):,.2f}).",
        f"3. Provider pattern: cluster '{signals.get('provider_cluster_label', 'Unknown')}'.",
        f"4. Billing anomalies: {int(signals.get('anomaly_flagged_days') or 0)} flagged day(s) in the "
        f"window, and {anomaly}.",
    ])


def recommend(
    claim: dict[str, Any],
    signals: dict[str, Any],
    thresholds: PolicyThresholds = PolicyThresholds(),
    *,
    injection_detected: bool = False,
) -> RecommendationOutput:
    violations = evaluate_signals(claim, signals, thresholds, injection_detected=injection_detected)
    blocking = [v for v in violations if v.severity == "block"]
    factors = [v.rule for v in violations]

    if blocking:
        return RecommendationOutput(
            recommendation="flag_for_review",
            summary=f"Rule engine flagged the claim: {'; '.join(v.message for v in blocking)}."[:400],
            confidence=0.6,
            key_factors=factors[:5],
        )

    ratio = _ratio(claim, signals)
    if signals.get("predicted_risk_label") == "Low" and ratio is not None and ratio <= SAFE_APPROVAL_RATIO:
        return RecommendationOutput(
            recommendation="approve",
            summary="Rule engine approved: low predicted risk, normal billing pattern and amount in line "
            "with the predicted payment.",
            confidence=0.55,
            key_factors=(["low_risk", "amount_in_line", *factors])[:5],
        )

    return RecommendationOutput(
        recommendation="flag_for_review",
        summary="Rule engine could not confirm the claim is routine; sending it to a human reviewer.",
        confidence=0.5,
        key_factors=(["not_clearly_routine", *factors])[:5],
    )
