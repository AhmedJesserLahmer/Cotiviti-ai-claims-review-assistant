import asyncio

import pytest

from ai_platform.errors import LLMTimeoutError
from ai_platform.resilience.timeout import with_timeout


async def test_returns_value_within_deadline():
    async def fast():
        return 42

    assert await with_timeout(fast(), 1) == 42


async def test_raises_llm_timeout_with_origin():
    async def slow():
        await asyncio.sleep(1)

    with pytest.raises(LLMTimeoutError) as info:
        await with_timeout(slow(), 0.01, provider="groq", model="m")
    assert info.value.retryable
    assert info.value.provider == "groq"
