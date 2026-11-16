"""Error mapping is tested with look-alike exception classes (no SDK needed)."""

import pytest

from ai_platform.errors import (
    LLMAuthError,
    LLMBadRequestError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from ai_platform.providers.groq import map_provider_exception


class APITimeoutError(Exception):
    pass


class RateLimitError(Exception):
    def __init__(self, retry_after):
        super().__init__("slow down")
        self.response = type("R", (), {"headers": {"retry-after": retry_after}})()


class AuthenticationError(Exception):
    pass


class APIConnectionError(Exception):
    pass


class StatusError(Exception):
    def __init__(self, status_code):
        super().__init__(f"http {status_code}")
        self.status_code = status_code


def _map(exc):
    return map_provider_exception(exc, provider="groq", model="m")


@pytest.mark.parametrize(
    "exc, expected",
    [
        (APITimeoutError(), LLMTimeoutError),
        (AuthenticationError(), LLMAuthError),
        (APIConnectionError(), LLMUnavailableError),
        (StatusError(503), LLMUnavailableError),
        (StatusError(429), LLMRateLimitError),
        (StatusError(404), LLMBadRequestError),
        (StatusError(401), LLMAuthError),
        (RuntimeError("weird"), LLMError),
    ],
)
def test_maps_sdk_errors(exc, expected):
    mapped = _map(exc)
    assert type(mapped) is expected
    assert mapped.provider == "groq" and mapped.model == "m"


def test_rate_limit_reads_retry_after_header():
    mapped = _map(RateLimitError("7"))
    assert isinstance(mapped, LLMRateLimitError)
    assert mapped.retry_after == 7.0
    assert _map(RateLimitError("soon")).retry_after is None


def test_unknown_errors_are_not_retried_and_ai_errors_pass_through():
    assert not _map(RuntimeError("x")).retryable
    original = LLMTimeoutError("t")
    assert _map(original) is original
