"""Rate-limit rules for the expensive claims-api endpoints."""

from fastapi import Depends

from claims_common.ratelimit import InMemoryRateLimiter, RateLimit, RateLimiter, RedisRateLimiter, rate_limit_dependency
from core.config import settings

_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RedisRateLimiter(settings.redis_url) if settings.redis_url else InMemoryRateLimiter()
    return _limiter


def _enabled() -> bool:
    return settings.rate_limit_enabled


analyze_limit = Depends(rate_limit_dependency(
    "analyze", RateLimit(settings.rate_limit_analyze_per_minute, burst=10), get_limiter, enabled=_enabled
))
bulk_limit = Depends(rate_limit_dependency(
    "bulk", RateLimit(settings.rate_limit_bulk_per_minute, burst=3), get_limiter, enabled=_enabled
))
