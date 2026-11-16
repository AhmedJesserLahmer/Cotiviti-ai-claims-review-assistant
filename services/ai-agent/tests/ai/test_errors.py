from ai_platform.errors import (
    AllProvidersFailedError,
    LLMAuthError,
    LLMRateLimitError,
    LLMTimeoutError,
    is_retryable,
)


def test_retryable_classification():
    assert is_retryable(LLMTimeoutError("slow"))
    assert is_retryable(LLMRateLimitError("429", retry_after=2))
    assert not is_retryable(LLMAuthError("bad key"))
    assert not is_retryable(ValueError("unrelated"))


def test_error_message_includes_origin():
    err = LLMTimeoutError("took too long", provider="groq", model="llama")
    assert str(err) == "[groq/llama] took too long"


def test_all_providers_failed_aggregates_messages():
    err = AllProvidersFailedError([LLMTimeoutError("a"), LLMAuthError("b")])
    assert "a" in str(err) and "b" in str(err)
    assert str(AllProvidersFailedError([])).endswith("no providers configured")
