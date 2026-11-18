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
    # asyncio.timeout runs the call in the caller's task. On Python 3.11, wait_for wraps
    # it in an inner task instead: cancelling a lost hedge then takes extra loop turns
    # and OpenTelemetry spans are closed from a different context (ValueError on detach).
    try:
        async with asyncio.timeout(seconds):
            return await awaitable
    except TimeoutError as exc:
        raise LLMTimeoutError(
            f"no response within {seconds:g}s", provider=provider, model=model
        ) from exc
