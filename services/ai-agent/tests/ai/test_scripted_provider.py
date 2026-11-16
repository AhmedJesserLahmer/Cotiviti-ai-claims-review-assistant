import pytest

from ai_platform.errors import LLMTimeoutError
from ai_platform.providers.base import ChatMessage, LLMProvider
from ai_platform.providers.scripted import ScriptedProvider


async def test_replays_script_in_order():
    provider = ScriptedProvider([LLMTimeoutError("t"), "hello"])
    assert isinstance(provider, LLMProvider)
    with pytest.raises(LLMTimeoutError):
        await provider.generate([ChatMessage.user("hi")])
    response = await provider.generate([ChatMessage.user("hi")])
    assert response.text == "hello"
    assert len(provider.calls) == 2
    assert provider.remaining == 0


async def test_exhausted_script_fails_loudly():
    with pytest.raises(AssertionError):
        await ScriptedProvider([]).generate([])
