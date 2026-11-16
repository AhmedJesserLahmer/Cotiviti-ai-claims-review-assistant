"""Provider for any OpenAI-compatible chat-completions API.

Used as a cross-vendor fallback: if the whole Groq account is throttled or down,
the chain continues on a different vendor (OpenAI, a gateway, vLLM, Ollama, ...)
instead of dropping straight to the rule engine. Implemented directly on httpx so it
adds no SDK dependency.
"""

from __future__ import annotations

import time

import httpx

from ai_platform.errors import (
    LLMAuthError,
    LLMBadRequestError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from ai_platform.providers.base import ChatMessage, LLMResponse, TokenUsage


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float,
        temperature: float = 0.2,
        name: str = "openai-compatible",
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.name = name
        self.model = model
        self._temperature = temperature
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_s, transport=transport
        )

    def _error(self, message: str, status: int | None = None, retry_after: str | None = None) -> LLMError:
        origin = {"provider": self.name, "model": self.model}
        if status == 429:
            try:
                delay = float(retry_after) if retry_after else None
            except ValueError:
                delay = None
            return LLMRateLimitError(message, retry_after=delay, **origin)
        if status in (401, 403):
            return LLMAuthError(message, **origin)
        if status is not None and 400 <= status < 500:
            return LLMBadRequestError(message, **origin)
        return LLMUnavailableError(message, **origin)

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self._temperature if temperature is None else temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        started = time.perf_counter()
        try:
            response = await self._client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(str(exc) or "timeout", provider=self.name, model=self.model) from exc
        except httpx.TransportError as exc:
            raise self._error(f"{type(exc).__name__}: {exc}") from exc
        if response.status_code >= 400:
            raise self._error(
                f"HTTP {response.status_code}: {response.text[:200]}",
                response.status_code,
                response.headers.get("retry-after"),
            )
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailableError(f"malformed completion: {exc}", provider=self.name, model=self.model) from exc
        usage = body.get("usage") or {}
        return LLMResponse(
            text=text,
            provider=self.name,
            model=body.get("model", self.model),
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            usage=TokenUsage(int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))),
        )
