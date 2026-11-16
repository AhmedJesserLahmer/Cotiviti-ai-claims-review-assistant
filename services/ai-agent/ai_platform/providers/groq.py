"""Groq adapter (via langchain-groq).

SDK-level retries are disabled (``max_retries=0``): retries, timeouts and fallbacks are
owned by ``ResilientLLMClient`` so attempts are visible in the audit trail and are not
multiplied (SDK retries x our retries).
"""

from __future__ import annotations

import time
from typing import Any

from ai_platform.errors import (
    LLMAuthError,
    LLMBadRequestError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from ai_platform.providers.base import ChatMessage, LLMResponse, TokenUsage

# Matched by class name so this module does not need the groq/httpx SDKs at import time.
_TIMEOUT_NAMES = {"APITimeoutError", "TimeoutError", "ReadTimeout", "ConnectTimeout", "TimeoutException"}
_RATE_LIMIT_NAMES = {"RateLimitError"}
_UNAVAILABLE_NAMES = {
    "APIConnectionError", "InternalServerError", "ServiceUnavailableError",
    "ConnectError", "RemoteProtocolError",
}
_AUTH_NAMES = {"AuthenticationError", "PermissionDeniedError"}
_BAD_REQUEST_NAMES = {"BadRequestError", "NotFoundError", "UnprocessableEntityError", "ConflictError"}


def _retry_after(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    value = headers.get("retry-after") if hasattr(headers, "get") else None
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def map_provider_exception(exc: BaseException, *, provider: str, model: str) -> LLMError:
    """Translate an SDK/transport exception into the ai_platform error taxonomy."""
    if isinstance(exc, LLMError):
        return exc
    names = {cls.__name__ for cls in type(exc).__mro__}
    status = getattr(exc, "status_code", None)
    message = f"{type(exc).__name__}: {exc}"
    origin = {"provider": provider, "model": model}

    if names & _TIMEOUT_NAMES:
        return LLMTimeoutError(message, **origin)
    if names & _RATE_LIMIT_NAMES or status == 429:
        return LLMRateLimitError(message, retry_after=_retry_after(exc), **origin)
    if names & _AUTH_NAMES or status in (401, 403):
        return LLMAuthError(message, **origin)
    if names & _BAD_REQUEST_NAMES or (isinstance(status, int) and 400 <= status < 500):
        return LLMBadRequestError(message, **origin)
    if names & _UNAVAILABLE_NAMES or (isinstance(status, int) and status >= 500):
        return LLMUnavailableError(message, **origin)
    # Unknown failure: do not hammer the same provider, let the chain move on.
    return LLMError(message, **origin)


def _to_langchain(messages: list[ChatMessage]) -> list[Any]:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    kinds = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
    return [kinds[m.role](content=m.content) for m in messages]


def _usage(result: Any) -> TokenUsage:
    usage = getattr(result, "usage_metadata", None) or {}
    if usage:
        return TokenUsage(int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))
    token_usage = (getattr(result, "response_metadata", None) or {}).get("token_usage") or {}
    return TokenUsage(int(token_usage.get("prompt_tokens", 0)), int(token_usage.get("completion_tokens", 0)))


class GroqProvider:
    name = "groq"

    def __init__(self, *, model: str, api_key: str, timeout_s: float, temperature: float = 0.2):
        self.model = model
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._temperature = temperature
        self._clients: dict[tuple[float, int | None], Any] = {}

    def _client(self, temperature: float, max_tokens: int | None) -> Any:
        key = (temperature, max_tokens)
        if key not in self._clients:
            from langchain_groq import ChatGroq

            self._clients[key] = ChatGroq(
                model=self.model,
                api_key=self._api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self._timeout_s,
                max_retries=0,
            )
        return self._clients[key]

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        started = time.perf_counter()
        try:
            client = self._client(self._temperature if temperature is None else temperature, max_tokens)
            result = await client.ainvoke(_to_langchain(messages))
        except Exception as exc:
            raise map_provider_exception(exc, provider=self.name, model=self.model) from exc

        content = result.content if isinstance(result.content, str) else str(result.content)
        return LLMResponse(
            text=content,
            provider=self.name,
            model=self.model,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            usage=_usage(result),
        )
