"""Per-client rate limiting for expensive endpoints.

Every AI analysis costs LLM tokens, so a single client must not be able to trigger
thousands of them. Limits are expressed as ``RateLimit(per_minute, burst)``:

* ``InMemoryRateLimiter``  token bucket per (rule, client), exact but per replica
* ``RedisRateLimiter``     fixed one-minute window shared by all replicas

Clients are identified by API key / bearer token (hashed, never stored raw), falling
back to the client IP (correct behind a proxy when uvicorn runs with --proxy-headers).
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request

log = logging.getLogger("claims.ratelimit")


@dataclass(frozen=True)
class RateLimit:
    per_minute: int
    burst: int | None = None

    @property
    def capacity(self) -> int:
        return self.burst or self.per_minute


@dataclass(frozen=True)
class Decision:
    allowed: bool
    remaining: int
    retry_after_s: int = 0


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: RateLimit) -> Decision: ...


class InMemoryRateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic, max_keys: int = 50_000):
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}
        self._max_keys = max_keys

    async def hit(self, key: str, limit: RateLimit) -> Decision:
        now = self._clock()
        rate = limit.per_minute / 60.0
        tokens, updated = self._buckets.get(key, (float(limit.capacity), now))
        tokens = min(float(limit.capacity), tokens + (now - updated) * rate)
        if tokens >= 1:
            self._store(key, tokens - 1, now)
            return Decision(True, int(tokens - 1))
        self._store(key, tokens, now)
        return Decision(False, 0, max(1, math.ceil((1 - tokens) / rate)))

    def _store(self, key: str, tokens: float, now: float) -> None:
        if len(self._buckets) >= self._max_keys and key not in self._buckets:
            self._buckets.clear()  # crude bound on memory; limits restart from full buckets
        self._buckets[key] = (tokens, now)


class RedisRateLimiter:
    def __init__(self, url: str | None = None, *, client=None, clock: Callable[[], float] = time.time):
        if client is None:
            from redis.asyncio import Redis

            client = Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)
        self._redis = client
        self._clock = clock
        self._fallback = InMemoryRateLimiter()

    async def hit(self, key: str, limit: RateLimit) -> Decision:
        now = self._clock()
        window = int(now // 60)
        redis_key = f"rl:{key}:{window}"
        try:
            count = await self._redis.incr(redis_key)
            if count == 1:
                await self._redis.expire(redis_key, 61)
        except Exception as exc:  # noqa: BLE001 - never let the limiter take the API down
            log.warning("redis rate limiter unavailable, using in-memory", extra={"error": str(exc)})
            return await self._fallback.hit(key, limit)
        if count <= limit.capacity:
            return Decision(True, limit.capacity - count)
        return Decision(False, 0, max(1, int(60 - now % 60)))


def client_identity(request: Request) -> str:
    credential = request.headers.get("x-api-key") or request.headers.get("authorization")
    if credential:
        return "key:" + hashlib.sha256(credential.encode()).hexdigest()[:16]
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def rate_limit_dependency(
    name: str,
    limit: RateLimit,
    limiter_factory: Callable[[], RateLimiter],
    *,
    enabled: Callable[[], bool] = lambda: True,
    identity: Callable[[Request], str] = client_identity,
):
    """FastAPI dependency enforcing ``limit`` for route group ``name``."""

    async def dependency(request: Request) -> None:
        if not enabled():
            return
        decision = await limiter_factory().hit(f"{name}:{identity(request)}", limit)
        if not decision.allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {name}: {limit.per_minute} requests/minute",
                headers={"Retry-After": str(decision.retry_after_s), "X-RateLimit-Limit": str(limit.per_minute)},
            )

    return dependency
