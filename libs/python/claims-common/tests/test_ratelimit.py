import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from claims_common.ratelimit import InMemoryRateLimiter, RateLimit, RedisRateLimiter, rate_limit_dependency


class Clock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


async def test_token_bucket_allows_burst_then_refills():
    clock = Clock()
    limiter = InMemoryRateLimiter(clock=clock)
    limit = RateLimit(per_minute=60, burst=2)
    assert (await limiter.hit("k", limit)).allowed
    assert (await limiter.hit("k", limit)).allowed
    denied = await limiter.hit("k", limit)
    assert not denied.allowed and denied.retry_after_s == 1
    clock.now = 1.0
    assert (await limiter.hit("k", limit)).allowed
    assert (await limiter.hit("other", limit)).allowed  # keys are independent


async def test_redis_fixed_window_and_fallback():
    class FakeRedis:
        def __init__(self):
            self.counts = {}

        async def incr(self, key):
            self.counts[key] = self.counts.get(key, 0) + 1
            return self.counts[key]

        async def expire(self, key, ttl):
            return True

    limiter = RedisRateLimiter(client=FakeRedis(), clock=Clock(120.0))
    limit = RateLimit(per_minute=2)
    assert [(await limiter.hit("k", limit)).allowed for _ in range(3)] == [True, True, False]

    class Down:
        async def incr(self, key):
            raise ConnectionError("down")

    assert (await RedisRateLimiter(client=Down()).hit("k", limit)).allowed


def test_dependency_returns_429_with_retry_after():
    limiter = InMemoryRateLimiter(clock=Clock())
    app = FastAPI()
    guard = rate_limit_dependency("analyze", RateLimit(per_minute=1), lambda: limiter)

    @app.post("/x", dependencies=[Depends(guard)])
    async def x():
        return {"ok": True}

    client = TestClient(app)
    assert client.post("/x").status_code == 200
    blocked = client.post("/x")
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) >= 1
    assert client.post("/x", headers={"X-API-Key": "another-client"}).status_code == 200


@pytest.mark.parametrize("enabled", [False])
def test_dependency_can_be_disabled(enabled):
    app = FastAPI()
    guard = rate_limit_dependency("a", RateLimit(per_minute=1), InMemoryRateLimiter, enabled=lambda: enabled)

    @app.get("/y", dependencies=[Depends(guard)])
    async def y():
        return {}

    client = TestClient(app)
    assert all(client.get("/y").status_code == 200 for _ in range(3))
