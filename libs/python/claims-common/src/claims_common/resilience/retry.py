"""Async retry with capped exponential backoff and full jitter.

Full jitter (``delay = uniform(0, min(cap, base * multiplier ** n))``) spreads retries
from many concurrent requests over time, so a provider that is recovering is not hit
by a synchronized wave of retries.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


def is_retryable(exc: BaseException) -> bool:
    """Errors opt in to retries by exposing ``retryable = True``."""
    return bool(getattr(exc, "retryable", False))

SleepFn = Callable[[float], Awaitable[None]]
OnRetryFn = Callable[[int, BaseException, float], None]


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    multiplier: float = 2.0
    jitter: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

    def backoff(self, attempt: int, rng: Callable[[], float] = random.random) -> float:
        """Delay to wait after the given failed attempt (1-based)."""
        ceiling = min(self.max_delay_s, self.base_delay_s * (self.multiplier ** (attempt - 1)))
        return ceiling * rng() if self.jitter else ceiling


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    should_retry: Callable[[BaseException], bool] = is_retryable,
    on_retry: OnRetryFn | None = None,
    sleep: SleepFn = asyncio.sleep,
    rng: Callable[[], float] = random.random,
) -> T:
    """Call ``fn`` until it succeeds, a non-retryable error occurs, or attempts run out.

    The last exception is re-raised unchanged. A ``retry_after`` attribute on the error
    (set by rate-limit errors) is respected, but never beyond ``max_delay_s``.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return await fn()
        except Exception as exc:
            if attempt >= policy.max_attempts or not should_retry(exc):
                raise
            delay = policy.backoff(attempt, rng)
            retry_after = getattr(exc, "retry_after", None)
            if retry_after:
                delay = min(max(delay, float(retry_after)), policy.max_delay_s)
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            await sleep(delay)
