from ai_platform.audit import AIRunMetadata
from ai_platform.cache import InMemoryTTLCache, RedisCache, cache_key
from ai_platform.client import ResilientLLMClient
from ai_platform.config import AISettings
from ai_platform.providers.base import ChatMessage
from ai_platform.providers.scripted import ScriptedProvider
from ai_platform.service import ClaimReviewAI
from tests.ai.test_service import APPROVE, CLAIM, PROVIDER, SIGNALS


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


async def test_ttl_and_lru_eviction():
    clock = Clock()
    cache = InMemoryTTLCache(max_entries=2, clock=clock)
    await cache.set("a", "1", ttl_s=10)
    await cache.set("b", "2", ttl_s=10)
    await cache.get("a")
    await cache.set("c", "3", ttl_s=10)  # evicts b (least recently used)
    assert await cache.get("b") is None and await cache.get("a") == "1"
    clock.now = 11
    assert await cache.get("a") is None


def test_key_depends_on_prompt_models_and_content():
    msgs = [ChatMessage.user("x")]
    base = cache_key("p@1", msgs, model_chain=["m"])
    assert base == cache_key("p@1", msgs, model_chain=["m"])
    assert base != cache_key("p@2", msgs, model_chain=["m"])
    assert base != cache_key("p@1", msgs, model_chain=["other"])
    assert base != cache_key("p@1", [ChatMessage.user("y")], model_chain=["m"])


async def test_redis_cache_failures_are_swallowed():
    class Broken:
        async def get(self, key):
            raise ConnectionError("down")

        async def set(self, *a, **k):
            raise ConnectionError("down")

    cache = RedisCache("redis://x", client=Broken())
    assert await cache.get("k") is None
    await cache.set("k", "v", 10)


async def _analyze(ai, run):
    reasoning = await ai.reason(claim=CLAIM, provider=PROVIDER, signals=SIGNALS, run=run)
    return await ai.recommend(claim=CLAIM, signals=SIGNALS, reasoning=reasoning, allow_more_data=True, run=run)


async def test_second_analysis_is_served_from_cache_and_bypass_works():
    provider = ScriptedProvider(["1. ok", APPROVE, "1. fresh", APPROVE])
    ai = ClaimReviewAI(ResilientLLMClient([provider]), AISettings(_env_file=None, groq_api_key="x"), InMemoryTTLCache())
    await _analyze(ai, AIRunMetadata())
    cached_run = AIRunMetadata()
    out = await _analyze(ai, cached_run)
    assert out.recommendation == "approve" and len(provider.calls) == 2
    assert cached_run.cache_hits == ["claim_reasoning", "claim_recommendation"]
    await _analyze(ai, AIRunMetadata(cache_bypassed=True))
    assert len(provider.calls) == 4
