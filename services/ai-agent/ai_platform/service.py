"""ClaimReviewAI: the single entry point the agent uses for LLM work.

Pipeline for each step:

    reason()     input guardrails -> versioned prompt -> resilient client (retry, timeout,
                 breaker, model fallback) -> output guardrail -> reasoning text
                 (rule-based reasoning if every LLM fails)

    recommend()  versioned prompt -> structured output with repair loop -> schema
                 (rule engine if the LLM is unavailable or keeps answering invalid JSON)
                 -> policy guardrail (escalate-only) -> final decision

Everything that happens is written to the ``AIRunMetadata`` passed in.
"""

from __future__ import annotations

import json
from typing import Any

from ai_platform.audit import AIRunMetadata
from ai_platform.cache import NullCache, ResponseCache, build_cache, cache_key
from ai_platform.client import ResilientLLMClient, build_client
from ai_platform.config import AISettings, get_ai_settings
from ai_platform.errors import AllProvidersFailedError, OutputValidationError
from ai_platform.fallback import rules
from ai_platform.guardrails.base import GuardrailFinding
from ai_platform.guardrails.injection import sanitize_payload
from ai_platform.guardrails.output import sanitize_reasoning
from ai_platform.guardrails.pii import redact_payload
from ai_platform.guardrails.policy import PolicyDecision, PolicyThresholds, enforce_policy
from ai_platform.prompts import CLAIM_REASONING, CLAIM_RECOMMENDATION
from ai_platform.validation.schemas import RecommendationOutput, schema_hint
from ai_platform.validation.structured import generate_structured

# Fields never sent to the LLM. ``risk_label`` is the training label of the synthetic
# dataset (ground truth), not something a reviewer would know at decision time.
_EXCLUDED_CLAIM_FIELDS = frozenset({"risk_label", "_id"})
_PROVIDER_FIELDS = ("provider_id", "name", "specialty", "region")
_LOOP_NOTE = "Note: additional data has already been fetched once; you must not choose request_more_data."


class ClaimReviewAI:
    def __init__(self, client: ResilientLLMClient, settings: AISettings, cache: ResponseCache | None = None):
        self.client = client
        self.settings = settings
        self.thresholds = PolicyThresholds.from_settings(settings)
        self.cache = cache or NullCache()

    def _key(self, prompt_id: str, messages) -> str:
        return cache_key(prompt_id, messages, model_chain=[slot.label for slot in self.client.slots])

    async def _cached(self, key: str, run: AIRunMetadata, prompt_name: str) -> str | None:
        if run.cache_bypassed:
            return None
        value = await self.cache.get(key)
        if value is not None:
            run.cache_hits.append(prompt_name)
        return value

    # ------------------------------------------------------------------ inputs
    def _protect(self, data: dict[str, Any], run: AIRunMetadata, *, keep_keys: frozenset[str] = frozenset()):
        payload = data
        if self.settings.guardrails_enabled:
            payload, findings = sanitize_payload(payload, max_chars=self.settings.max_field_chars)
            run.add_events(findings)
        if self.settings.pii_redaction_enabled:
            payload, findings = redact_payload(payload, keep_keys=keep_keys)
            run.add_events(findings)
        return payload

    def prepare_inputs(self, claim: dict, provider: dict, run: AIRunMetadata) -> tuple[dict, dict]:
        claim_view = {k: v for k, v in claim.items() if k not in _EXCLUDED_CLAIM_FIELDS}
        provider_view = {k: provider.get(k) for k in _PROVIDER_FIELDS if k in provider}
        # Provider names are business names, not personal data.
        return self._protect(claim_view, run), self._protect(provider_view, run, keep_keys=frozenset({"name"}))

    # --------------------------------------------------------------- reasoning
    async def reason(self, *, claim: dict, provider: dict, signals: dict, run: AIRunMetadata) -> str:
        claim_view, provider_view = self.prepare_inputs(claim, provider, run)
        run.use_prompt(CLAIM_REASONING.name, CLAIM_REASONING.version)

        if self.client.is_empty:
            run.mark_degraded("LLM disabled (no credentials or offline mode)")
            return rules.build_reasoning(claim, signals)

        messages = CLAIM_REASONING.render(
            claim_json=json.dumps(claim_view, default=str),
            provider_json=json.dumps(provider_view, default=str),
            signals_json=json.dumps(signals, default=str),
        )
        key = self._key(CLAIM_REASONING.id, messages)
        cached = await self._cached(key, run, CLAIM_REASONING.name)
        if cached is not None:
            return cached
        try:
            response = await self.client.generate(messages, recorder=run, temperature=self.settings.temperature)
            text, findings = sanitize_reasoning(response.text, max_chars=self.settings.max_reasoning_chars)
        except (AllProvidersFailedError, OutputValidationError) as exc:
            run.mark_degraded(f"reasoning: {exc}")
            return rules.build_reasoning(claim, signals)
        run.add_events(findings)
        await self.cache.set(key, text, self.settings.cache_ttl_s)
        return text

    # ---------------------------------------------------------- recommendation
    async def recommend(
        self,
        *,
        claim: dict,
        signals: dict,
        reasoning: str,
        allow_more_data: bool,
        run: AIRunMetadata,
    ) -> RecommendationOutput:
        output = await self._llm_or_rules(claim, signals, reasoning, allow_more_data, run)
        decision = self._apply_policy(output, claim, signals, allow_more_data, run)

        run.confidence = decision.output.confidence
        run.key_factors = list(decision.output.key_factors)
        run.policy_violations = [f"{v.severity}:{v.rule}" for v in decision.violations]
        if decision.overridden:
            run.recommendation_overridden = True
            run.original_recommendation = decision.original_recommendation
        return decision.output

    async def _llm_or_rules(
        self, claim: dict, signals: dict, reasoning: str, allow_more_data: bool, run: AIRunMetadata
    ) -> RecommendationOutput:
        def fallback(reason: str | None = None) -> RecommendationOutput:
            if reason:
                run.mark_degraded(reason)
            return rules.recommend(claim, signals, self.thresholds, injection_detected=run.injection_detected)

        if self.client.is_empty:
            return fallback("LLM disabled (no credentials or offline mode)")
        if run.degraded:
            # Reasoning already fell back: providers are down, do not pay the timeouts twice.
            return fallback()

        run.use_prompt(CLAIM_RECOMMENDATION.name, CLAIM_RECOMMENDATION.version)
        messages = CLAIM_RECOMMENDATION.render(
            reasoning=reasoning,
            signals_json=json.dumps(signals, default=str),
            loop_note="" if allow_more_data else _LOOP_NOTE,
        )
        key = self._key(CLAIM_RECOMMENDATION.id, messages)
        cached = await self._cached(key, run, CLAIM_RECOMMENDATION.name)
        if cached is not None:
            return RecommendationOutput.model_validate_json(cached)
        try:
            output = await generate_structured(
                self.client,
                messages,
                RecommendationOutput,
                max_repairs=self.settings.max_repair_attempts,
                schema_hint=schema_hint(),
                recorder=run,
                counter=run,
                temperature=self.settings.temperature,
            )
        except (AllProvidersFailedError, OutputValidationError) as exc:
            return fallback(f"recommendation: {exc}")
        # Cache the model's own answer; policy is re-applied on every run.
        await self.cache.set(key, output.model_dump_json(), self.settings.cache_ttl_s)
        return output

    def _apply_policy(
        self, output: RecommendationOutput, claim: dict, signals: dict, allow_more_data: bool, run: AIRunMetadata
    ) -> PolicyDecision:
        if self.settings.policy_enforcement_enabled:
            decision = enforce_policy(
                output, claim, signals, self.thresholds,
                allow_more_data=allow_more_data, injection_detected=run.injection_detected,
            )
        else:
            # Even with policy off, the data budget must hold or the agent could loop.
            decision = enforce_policy(
                output, {}, {}, self.thresholds, allow_more_data=allow_more_data, injection_detected=False
            )
        for violation in decision.violations:
            action = "overridden" if decision.overridden and violation.severity == "block" else "warned"
            run.add_event(GuardrailFinding("policy", action, f"{violation.rule}: {violation.message}"))
        return decision

    def health(self) -> dict:
        return {
            "llm_enabled": not self.client.is_empty,
            "model_chain": [slot.label for slot in self.client.slots],
            "circuits": self.client.health(),
            "policy_enforcement": self.settings.policy_enforcement_enabled,
            "guardrails": self.settings.guardrails_enabled,
            "cache": type(self.cache).__name__,
        }


_instance: ClaimReviewAI | None = None


def get_claim_review_ai() -> ClaimReviewAI:
    """Process-wide instance, so circuit breakers keep state across requests."""
    global _instance
    if _instance is None:
        settings = get_ai_settings()
        _instance = ClaimReviewAI(build_client(settings), settings, build_cache(settings))
    return _instance
