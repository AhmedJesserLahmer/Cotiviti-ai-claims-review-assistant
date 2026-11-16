"""Deterministic provider that replays a script of responses and errors.

Used by the test suite and for chaos drills (e.g. simulate a provider that times out
twice and then recovers) without network access or API keys.
"""

from __future__ import annotations

from collections.abc import Iterable

from ai_platform.providers.base import ChatMessage, LLMResponse

ScriptItem = str | BaseException


class ScriptedProvider:
    def __init__(self, script: Iterable[ScriptItem], *, name: str = "scripted", model: str = "scripted-1"):
        self.name = name
        self.model = model
        self._script = list(script)
        self.calls: list[list[ChatMessage]] = []

    @property
    def remaining(self) -> int:
        return len(self._script)

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls.append(list(messages))
        if not self._script:
            raise AssertionError(f"ScriptedProvider '{self.name}' ran out of scripted responses")
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return LLMResponse(text=item, provider=self.name, model=self.model, latency_ms=1.0)
