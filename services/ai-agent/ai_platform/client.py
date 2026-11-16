"""Resilient LLM client: one call site, many failure modes handled.

For each provider in the chain (primary model first, then fallbacks):

1. skip it if its circuit breaker is open,
2. call it under a hard timeout,
3. retry retryable errors with backoff + jitter,
4. on final failure record it on the breaker and move to the next provider.

If every provider fails, ``AllProvidersFailedError`` is raised and the caller decides
how to degrade (see ``ai_platform.fallback``).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from ai_platform.errors import AllProvidersFailedError, CircuitOpenError, is_retryable
from ai_platform.providers.base import ChatMessage, LLMProvider, LLMResponse
from ai_platform.resilience.circuit_breaker import CircuitBreaker
from ai_platform.resilience.retry import RetryPolicy, SleepFn, retry_async
from ai_platform.resilience.timeout import with_timeout


class AttemptRecorder(Protocol):
    def record_attempt(
        self,
        *,
        provider: str,
        model: str,
        attempt: int,
        outcome: str,
        latency_ms: float,
        error: str | None = None,
    ) -> None: ...


@dataclass
class ProviderSlot:
    provider: LLMProvider
    breaker: CircuitBreaker

    @property
    def label(self) -> str:
        return f"{self.provider.name}/{self.provider.model}"


class ResilientLLMClient:
    def __init__(
        self,
        providers: list[LLMProvider],
        *,
        retry_policy: RetryPolicy | None = None,
        timeout_s: float = 20.0,
        breaker_factory: Callable[[str], CircuitBreaker] | None = None,
        sleep: SleepFn | None = None,
    ):
        factory = breaker_factory or (lambda name: CircuitBreaker(name))
        self.slots = [ProviderSlot(p, factory(f"{p.name}/{p.model}")) for p in providers]
        self.retry_policy = retry_policy or RetryPolicy()
        self.timeout_s = timeout_s
        self._sleep = sleep

    @property
    def is_empty(self) -> bool:
        return not self.slots

    def health(self) -> list[dict]:
        return [slot.breaker.snapshot() for slot in self.slots]

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        recorder: AttemptRecorder | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        errors: list[Exception] = []
        for slot in self.slots:
            provider = slot.provider
            if not slot.breaker.allow_request():
                err = CircuitOpenError(f"circuit open for {slot.label}")
                errors.append(err)
                if recorder:
                    recorder.record_attempt(
                        provider=provider.name, model=provider.model, attempt=0,
                        outcome="circuit_open", latency_ms=0.0, error=str(err),
                    )
                continue

            attempt_no = 0

            async def call_once(slot: ProviderSlot = slot) -> LLMResponse:
                nonlocal attempt_no
                attempt_no += 1
                started = time.perf_counter()
                try:
                    response = await with_timeout(
                        slot.provider.generate(messages, temperature=temperature, max_tokens=max_tokens),
                        self.timeout_s,
                        provider=slot.provider.name,
                        model=slot.provider.model,
                    )
                except Exception as exc:
                    if recorder:
                        recorder.record_attempt(
                            provider=slot.provider.name, model=slot.provider.model, attempt=attempt_no,
                            outcome="error", latency_ms=_elapsed_ms(started), error=str(exc),
                        )
                    raise
                if recorder:
                    recorder.record_attempt(
                        provider=slot.provider.name, model=slot.provider.model, attempt=attempt_no,
                        outcome="success", latency_ms=_elapsed_ms(started),
                    )
                    if hasattr(recorder, "record_usage"):
                        recorder.record_usage(
                            model=response.model,
                            prompt_tokens=response.usage.prompt_tokens,
                            completion_tokens=response.usage.completion_tokens,
                        )
                return response

            kwargs = {"sleep": self._sleep} if self._sleep else {}
            try:
                response = await retry_async(call_once, self.retry_policy, should_retry=is_retryable, **kwargs)
            except Exception as exc:
                slot.breaker.record_failure()
                errors.append(exc)
                continue
            slot.breaker.record_success()
            return response

        raise AllProvidersFailedError(errors)


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


def build_client(settings) -> ResilientLLMClient:
    """Client for the configured Groq model chain; empty when the LLM is disabled.

    An empty client is valid: callers detect it with ``is_empty`` and go straight to
    the deterministic fallback instead of failing the request.
    """
    from ai_platform.providers.groq import GroqProvider
    from ai_platform.providers.openai_compat import OpenAICompatibleProvider

    providers: list[LLMProvider] = []
    if settings.llm_enabled and settings.has_llm_credentials:
        providers += [
            GroqProvider(
                model=model,
                api_key=settings.groq_api_key,
                timeout_s=settings.request_timeout_s,
                temperature=settings.temperature,
            )
            for model in settings.model_chain
        ]
    if settings.llm_enabled and settings.openai_compatible_enabled:
        providers.append(
            OpenAICompatibleProvider(
                base_url=settings.openai_base_url,
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                timeout_s=settings.request_timeout_s,
                temperature=settings.temperature,
            )
        )
    return ResilientLLMClient(
        providers,
        retry_policy=RetryPolicy(
            max_attempts=settings.max_retries + 1,
            base_delay_s=settings.backoff_base_s,
            max_delay_s=settings.backoff_max_s,
        ),
        timeout_s=settings.request_timeout_s,
        breaker_factory=lambda name: CircuitBreaker(
            name,
            failure_threshold=settings.circuit_failure_threshold,
            recovery_timeout_s=settings.circuit_recovery_s,
        ),
    )
