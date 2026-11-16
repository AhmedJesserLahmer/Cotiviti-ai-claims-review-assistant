"""Vendor-neutral types shared by every LLM provider adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str

    @classmethod
    def system(cls, content: str) -> ChatMessage:
        return cls("system", content)

    @classmethod
    def user(cls, content: str) -> ChatMessage:
        return cls("user", content)

    @classmethod
    def assistant(cls, content: str) -> ChatMessage:
        return cls("assistant", content)


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    latency_ms: float = 0.0
    usage: TokenUsage = field(default_factory=TokenUsage)


@runtime_checkable
class LLMProvider(Protocol):
    """Anything that turns chat messages into a completion.

    Implementations must raise ``ai_platform.errors.LLMError`` subclasses, never raw SDK
    exceptions, so retry and fallback logic stays vendor-neutral.
    """

    name: str
    model: str

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse: ...
