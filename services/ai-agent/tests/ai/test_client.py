import pytest

from ai_platform.client import ResilientLLMClient
from ai_platform.errors import AllProvidersFailedError, LLMAuthError, LLMTimeoutError, LLMUnavailableError
from ai_platform.providers.base import ChatMessage
from ai_platform.providers.scripted import ScriptedProvider
from ai_platform.resilience.circuit_breaker import CircuitBreaker
from ai_platform.resilience.retry import RetryPolicy


class Recorder:
    def __init__(self):
        self.attempts = []

    def record_attempt(self, **kwargs):
        self.attempts.append(kwargs)


async def _no_sleep(_):
    return None


def make_client(*providers, attempts=3, threshold=5):
    return ResilientLLMClient(
        list(providers),
        retry_policy=RetryPolicy(max_attempts=attempts),
        timeout_s=1,
        breaker_factory=lambda name: CircuitBreaker(name, failure_threshold=threshold),
        sleep=_no_sleep,
    )


MSG = [ChatMessage.user("hi")]


async def test_primary_success_is_recorded():
    rec = Recorder()
    client = make_client(ScriptedProvider(["ok"], name="a"))
    response = await client.generate(MSG, recorder=rec)
    assert response.text == "ok"
    assert [a["outcome"] for a in rec.attempts] == ["success"]


async def test_retries_transient_errors_on_same_provider():
    rec = Recorder()
    primary = ScriptedProvider([LLMTimeoutError("t"), LLMUnavailableError("503"), "ok"], name="a")
    response = await make_client(primary).generate(MSG, recorder=rec)
    assert response.provider == "a"
    assert [a["attempt"] for a in rec.attempts] == [1, 2, 3]


async def test_falls_back_to_next_provider_after_retries_exhausted():
    primary = ScriptedProvider([LLMTimeoutError("t")] * 2, name="a")
    fallback = ScriptedProvider(["from-b"], name="b")
    response = await make_client(primary, fallback, attempts=2).generate(MSG)
    assert response.text == "from-b"


async def test_auth_error_skips_retries_and_falls_back():
    primary = ScriptedProvider([LLMAuthError("bad key")], name="a")
    fallback = ScriptedProvider(["from-b"], name="b")
    response = await make_client(primary, fallback).generate(MSG)
    assert response.provider == "b"
    assert len(primary.calls) == 1


async def test_open_circuit_skips_provider_without_calling_it():
    primary = ScriptedProvider([LLMAuthError("x")], name="a")
    fallback = ScriptedProvider(["one", "two"], name="b")
    client = make_client(primary, fallback, threshold=1)
    await client.generate(MSG)
    rec = Recorder()
    await client.generate(MSG, recorder=rec)
    assert len(primary.calls) == 1  # not called the second time
    assert rec.attempts[0]["outcome"] == "circuit_open"
    assert client.health()[0]["state"] == "open"


async def test_all_providers_failing_raises_aggregate_error():
    client = make_client(ScriptedProvider([LLMAuthError("a")], name="a"), ScriptedProvider([LLMAuthError("b")], name="b"))
    with pytest.raises(AllProvidersFailedError) as info:
        await client.generate(MSG)
    assert len(info.value.errors) == 2


async def test_empty_client():
    client = make_client()
    assert client.is_empty
    with pytest.raises(AllProvidersFailedError):
        await client.generate(MSG)


def test_build_client_from_settings(monkeypatch):
    from ai_platform.client import build_client
    from ai_platform.config import AISettings

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert build_client(AISettings(_env_file=None)).is_empty

    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
    monkeypatch.setenv("AI_FALLBACK_MODELS", "small-model")
    monkeypatch.setenv("AI_MAX_RETRIES", "1")
    client = build_client(AISettings(_env_file=None))
    assert [slot.provider.model for slot in client.slots][1] == "small-model"
    assert client.retry_policy.max_attempts == 2
