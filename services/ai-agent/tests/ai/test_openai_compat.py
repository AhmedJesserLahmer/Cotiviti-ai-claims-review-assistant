import httpx
import pytest

from ai_platform.client import build_client
from ai_platform.config import AISettings
from ai_platform.errors import LLMAuthError, LLMRateLimitError, LLMTimeoutError, LLMUnavailableError
from ai_platform.providers.base import ChatMessage
from ai_platform.providers.openai_compat import OpenAICompatibleProvider


def provider(handler):
    return OpenAICompatibleProvider(base_url="http://llm/v1", api_key="k", model="gpt-x", timeout_s=1,
                                    transport=httpx.MockTransport(handler))


async def test_successful_completion_with_usage():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["path"] = request.url.path
        return httpx.Response(200, json={"model": "gpt-x", "choices": [{"message": {"content": "hi"}}],
                                         "usage": {"prompt_tokens": 7, "completion_tokens": 2}})

    response = await provider(handler).generate([ChatMessage.user("hello")], max_tokens=50)
    assert response.text == "hi" and response.usage.total_tokens == 9
    assert seen == {"auth": "Bearer k", "path": "/v1/chat/completions"}


@pytest.mark.parametrize(
    "status, error", [(429, LLMRateLimitError), (401, LLMAuthError), (503, LLMUnavailableError)]
)
async def test_http_errors_are_mapped(status, error):
    with pytest.raises(error):
        await provider(lambda r: httpx.Response(status, headers={"retry-after": "2"})).generate([])


async def test_timeouts_and_malformed_bodies():
    def slow(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(LLMTimeoutError):
        await provider(slow).generate([])
    with pytest.raises(LLMUnavailableError):
        await provider(lambda r: httpx.Response(200, json={"oops": 1})).generate([])


def test_cross_vendor_fallback_is_appended_to_the_chain(monkeypatch):
    for key in ["GROQ_API_KEY", "AI_OFFLINE_MODE"]:
        monkeypatch.delenv(key, raising=False)
    only_openai = AISettings(_env_file=None, openai_base_url="http://llm/v1", openai_model="gpt-x")
    assert only_openai.llm_enabled
    assert [s.provider.name for s in build_client(only_openai).slots] == ["openai-compatible"]
    both = AISettings(_env_file=None, groq_api_key="g", openai_base_url="http://llm/v1", openai_model="gpt-x")
    assert [s.provider.name for s in build_client(both).slots][-1] == "openai-compatible"
