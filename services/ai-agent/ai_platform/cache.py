"""Cache for validated LLM results.

Only results that already passed validation and guardrails are cached (sanitized
reasoning text, schema-valid recommendation JSON), keyed by the prompt version and the
exact rendered messages. A re-analysis of an unchanged claim therefore costs no tokens
and returns the same decision; changing a prompt version or any input misses the cache.

Backends: ``InMemoryTTLCache`` (per process, default) and ``RedisCache`` (shared by
all replicas). Cache failures never fail an analysis: errors are swallowed and the
LLM is called as if the cache were empty.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Protocol

from ai_platform.providers.base import ChatMessage

log = logging.getLogger("ai_platform.cache")


def cache_key(prompt_id: str, messages: list[ChatMessage], *, model_chain: list[str]) -> str:
    payload = json.dumps(
        {"prompt": prompt_id, "models": model_chain, "messages": [[m.role, m.content] for m in messages]},
        sort_keys=True,
    )
    return "ai:v1:" + hashlib.sha256(payload.encode()).hexdigest()


class ResponseCache(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_s: int) -> None: ...


class NullCache:
    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl_s: int) -> None:
        return None


class InMemoryTTLCache:
    def __init__(self, max_entries: int = 1000, clock=time.monotonic):
        self.max_entries = max_entries
        self._clock = clock
        self._data: OrderedDict[str, tuple[float, str]] = OrderedDict()

    async def get(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires_at, value = item
        if self._clock() >= expires_at:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return value

    async def set(self, key: str, value: str, ttl_s: int) -> None:
        self._data[key] = (self._clock() + ttl_s, value)
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)


class RedisCache:
    def __init__(self, url: str, *, client=None):
        if client is None:
            from redis.asyncio import Redis

            client = Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)
        self._redis = client

    async def get(self, key: str) -> str | None:
        try:
            value = await self._redis.get(key)
        except Exception as exc:  # noqa: BLE001 - cache must never fail the request
            log.warning("cache get failed", extra={"error": str(exc)})
            return None
        return value.decode() if isinstance(value, bytes) else value

    async def set(self, key: str, value: str, ttl_s: int) -> None:
        try:
            await self._redis.set(key, value, ex=ttl_s)
        except Exception as exc:  # noqa: BLE001
            log.warning("cache set failed", extra={"error": str(exc)})


def build_cache(settings) -> ResponseCache:
    if not settings.cache_enabled:
        return NullCache()
    if settings.cache_redis_url:
        return RedisCache(settings.cache_redis_url)
    return InMemoryTTLCache(settings.cache_max_entries)
