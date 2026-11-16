import asyncio

import pytest

from ai_platform.client import ResilientLLMClient
from ai_platform.errors import AllProvidersFailedError, LLMAuthError
from ai_platform.providers.base import ChatMessage, LLMResponse
from ai_platform.resilience.retry import RetryPolicy

MSG = [ChatMessage.user("hi")]


class Timed:
    def __init__(self, name, delay, text="ok", error=None):
        self.name, self.model, self.delay, self.text, self.error = name, name, delay, text, error
        self.cancelled = False

    async def generate(self, messages, **kwargs):
        try:
            await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        if self.error:
            raise self.error
        return LLMResponse(text=self.text, provider=self.name, model=self.model)


def client(*providers, hedge=0.05):
    return ResilientLLMClient(list(providers), retry_policy=RetryPolicy(max_attempts=1), timeout_s=2, hedge_after_s=hedge)


async def test_fast_primary_never_starts_the_hedge():
    backup = Timed("b", 0.0)
    response = await client(Timed("a", 0.0), backup).generate(MSG)
    assert response.provider == "a" and not backup.cancelled


async def test_slow_primary_is_beaten_by_hedge_and_cancelled():
    primary = Timed("a", 1.0)
    c = client(primary, Timed("b", 0.0))
    response = await c.generate(MSG)
    await asyncio.sleep(0)
    assert response.provider == "b" and primary.cancelled
    assert c.slots[0].breaker.consecutive_failures == 0  # losing a race is not a failure


async def test_primary_can_still_win_after_hedge_started():
    response = await client(Timed("a", 0.08), Timed("b", 0.5)).generate(MSG)
    assert response.provider == "a"


async def test_all_hedged_paths_failing_aggregates_errors():
    with pytest.raises(AllProvidersFailedError) as info:
        await client(Timed("a", 0.1, error=LLMAuthError("x")), Timed("b", 0.0, error=LLMAuthError("y"))).generate(MSG)
    assert len(info.value.errors) == 2


async def test_fast_primary_failure_goes_to_backup():
    response = await client(Timed("a", 0.0, error=LLMAuthError("x")), Timed("b", 0.0)).generate(MSG)
    assert response.provider == "b"
