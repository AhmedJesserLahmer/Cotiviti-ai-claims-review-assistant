"""Policy guardrail: deterministic checks that the LLM decision may not override.

The LLM is good at explaining, but it can be wrong, manipulated, or simply
inconsistent with the ML models. This layer re-derives red flags directly from the
ML signals and enforces one invariant:

    Guardrails can only make a decision MORE conservative, never less.

Concretely, an ``approve`` is escalated to ``flag_for_review`` when a blocking rule
fires, and ``request_more_data`` is escalated when the data-fetch budget is spent.
Nothing here ever turns a flag into an approval, and nothing ever auto-denies: a
denial stays a human decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from ai_platform.validation.schemas import RecommendationOutput

Severity = Literal["block", "warn"]


@dataclass(frozen=True)
class PolicyThresholds:
    high_risk_probability: float = 0.6
    billing_ratio: float = 2.5

    @classmethod
    def from_settings(cls, settings) -> PolicyThresholds:
        return cls(
            high_risk_probability=settings.high_risk_probability_threshold,
            billing_ratio=settings.billing_ratio_threshold,
        )


@dataclass(frozen=True)
class PolicyViolation:
    rule: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class PolicyDecision:
    output: RecommendationOutput
    violations: list[PolicyViolation] = field(default_factory=list)
    overridden: bool = False
    original_recommendation: str | None = None


def evaluate_signals(
    claim: dict[str, Any],
    signals: dict[str, Any],
    thresholds: PolicyThresholds = PolicyThresholds(),
    *,
    injection_detected: bool = False,
) -> list[PolicyViolation]:
    """Red flags derived only from data and ML signals, independent of the LLM."""
    violations: list[PolicyViolation] = []

    probabilities = signals.get("risk_probabilities") or {}
    p_high = float(probabilities.get("High", 0.0))
    if signals.get("predicted_risk_label") == "High" or p_high >= thresholds.high_risk_probability:
        violations.append(
            PolicyViolation("high_risk", "block", f"classifier predicts High risk (P(High)={p_high:.2f})")
        )

    if signals.get("is_recent_anomaly"):
        score = float(signals.get("anomaly_recent_score", 0.0))
        violations.append(
            PolicyViolation("recent_anomaly", "block", f"provider billing is anomalous right now (score {score:.2f})")
        )

    billed = float(claim.get("billed_amount") or 0.0)
    predicted = float(signals.get("predicted_paid_amount") or 0.0)
    if predicted > 0 and billed > predicted * thresholds.billing_ratio:
        violations.append(
            PolicyViolation(
                "billing_gap",
                "block",
                f"billed ${billed:,.2f} is {billed / predicted:.1f}x the predicted payment ${predicted:,.2f}",
            )
        )

    if signals.get("signals_source") == "cache":
        violations.append(
            PolicyViolation("stale_ml_signals", "block", "ML scoring was unavailable; signals reused from a past run")
        )

    ood = signals.get("ood_flags") or []
    if ood:
        violations.append(
            PolicyViolation("ml_out_of_distribution", "block", f"ML input unlike training data: {'; '.join(ood[:3])}")
        )

    if injection_detected:
        violations.append(
            PolicyViolation("untrusted_input", "block", "claim fields contained a suspected prompt injection")
        )

    if "outlier" in str(signals.get("provider_cluster_label", "")).lower():
        violations.append(
            PolicyViolation("outlier_provider", "warn", "provider belongs to the high-denial outlier cluster")
        )

    if int(signals.get("anomaly_flagged_days") or 0) >= 5:
        violations.append(
            PolicyViolation(
                "anomaly_history", "warn", f"{signals['anomaly_flagged_days']} anomalous billing days in window"
            )
        )

    return violations


def enforce_policy(
    output: RecommendationOutput,
    claim: dict[str, Any],
    signals: dict[str, Any],
    thresholds: PolicyThresholds = PolicyThresholds(),
    *,
    allow_more_data: bool = True,
    injection_detected: bool = False,
) -> PolicyDecision:
    violations = evaluate_signals(claim, signals, thresholds, injection_detected=injection_detected)
    blocking = [v for v in violations if v.severity == "block"]

    if output.recommendation == "request_more_data" and not allow_more_data:
        blocking.append(
            PolicyViolation("data_budget", "block", "additional data was already fetched; a decision is required")
        )
        violations.append(blocking[-1])
        return _escalate(output, violations, blocking[-1:])

    if output.recommendation == "approve" and blocking:
        return _escalate(output, violations, blocking)

    return PolicyDecision(output=output, violations=violations)


def _escalate(
    output: RecommendationOutput, violations: list[PolicyViolation], reasons: list[PolicyViolation]
) -> PolicyDecision:
    reason_text = "; ".join(v.message for v in reasons)
    summary = f"Escalated to manual review by policy: {reason_text}. Model rationale: {output.summary}"
    escalated = output.model_copy(
        update={
            "recommendation": "flag_for_review",
            "summary": summary[:400],
            "key_factors": ([v.rule for v in reasons] + output.key_factors)[:5],
        }
    )
    return PolicyDecision(
        output=escalated,
        violations=violations,
        overridden=True,
        original_recommendation=output.recommendation,
    )
