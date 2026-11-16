"""Per-analysis audit trail.

``AIRunMetadata`` answers, for any stored recommendation: which prompts and models were
used, how many attempts and repairs it took, whether we fell back to another model or
to the rule engine, which guardrails fired, and whether policy overrode the model.

It implements the ``AttemptRecorder`` and ``RepairCounter`` protocols used by the client
and the structured-output loop, so it can be passed straight into them.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr

from ai_platform.guardrails.base import GuardrailFinding

AttemptOutcome = Literal["success", "error", "circuit_open"]
DecisionSource = Literal["llm", "rules"]


class AttemptRecord(BaseModel):
    provider: str
    model: str
    attempt: int
    outcome: AttemptOutcome
    latency_ms: float
    error: str | None = None


class GuardrailEvent(BaseModel):
    guardrail: str
    action: str
    detail: str


class AIRunMetadata(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    attempts: list[AttemptRecord] = Field(default_factory=list)
    provider_used: str | None = None
    model_used: str | None = None
    model_fallback_used: bool = False
    degraded: bool = False
    degraded_reason: str | None = None
    decision_source: DecisionSource = "llm"
    repair_attempts: int = 0
    guardrail_events: list[GuardrailEvent] = Field(default_factory=list)
    injection_detected: bool = False
    recommendation_overridden: bool = False
    original_recommendation: str | None = None
    policy_violations: list[str] = Field(default_factory=list)
    confidence: float | None = None
    key_factors: list[str] = Field(default_factory=list)
    total_latency_ms: float | None = None
    cache_hits: list[str] = Field(default_factory=list)
    cache_bypassed: bool = False

    _t0: float = PrivateAttr(default_factory=time.perf_counter)
    _primary_model: str | None = PrivateAttr(default=None)

    # --- recorder protocols ---------------------------------------------------
    def record_attempt(
        self, *, provider: str, model: str, attempt: int, outcome: str, latency_ms: float, error: str | None = None
    ) -> None:
        if self._primary_model is None:
            self._primary_model = model
        self.attempts.append(
            AttemptRecord(
                provider=provider, model=model, attempt=attempt, outcome=outcome,
                latency_ms=latency_ms, error=(error or None) and error[:300],
            )
        )
        if outcome == "success":
            self.provider_used, self.model_used = provider, model
            self.model_fallback_used = model != self._primary_model

    def record_repair(self, error: str) -> None:
        self.repair_attempts += 1
        self.add_event(GuardrailFinding("output_validation", "sanitized", f"repair requested: {error[:200]}"))

    # --- helpers --------------------------------------------------------------
    def use_prompt(self, name: str, version: str) -> None:
        self.prompt_versions[name] = version

    def add_event(self, finding: GuardrailFinding) -> None:
        self.guardrail_events.append(
            GuardrailEvent(guardrail=finding.guardrail, action=finding.action, detail=finding.detail)
        )
        if finding.guardrail == "prompt_injection" and finding.action == "blocked":
            self.injection_detected = True

    def add_events(self, findings: list[GuardrailFinding]) -> None:
        for finding in findings:
            self.add_event(finding)

    def mark_degraded(self, reason: str) -> None:
        self.degraded = True
        self.decision_source = "rules"
        if self.degraded_reason is None:
            self.degraded_reason = reason[:300]

    def finish(self) -> AIRunMetadata:
        self.total_latency_ms = round((time.perf_counter() - self._t0) * 1000, 1)
        return self
