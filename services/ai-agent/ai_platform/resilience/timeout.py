"""Hard deadline for a single LLM call.

SDK-level timeouts are not always honoured end-to-end (DNS, TLS, streaming), so every
call is also wrapped in an asyncio deadline that converts into ``LLMTimeoutError``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

from ai_platform.errors import LLMTimeoutError

T = TypeVar("T")


async def with_timeout(
    awaitable: Awaitable[T],
    seconds: float,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> T:
    try:
        return await asyncio.wait_for(awaitable, timeout=seconds)
    except asyncio.TimeoutError as exc:
        raise LLMTimeoutError(
            f"no response within {seconds:g}s", provider=provider, model=model
        ) from exc
