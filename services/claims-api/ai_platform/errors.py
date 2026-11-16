"""Error taxonomy for the AI layer.

Every failure coming out of an LLM call is mapped onto one of these types, so the
resilience code can decide what to do without knowing which vendor SDK raised it:

* ``retryable = True``  -> the same provider may succeed if we try again
  (timeouts, rate limits, 5xx, connection resets).
* ``retryable = False`` -> retrying the same provider is pointless
  (bad credentials, malformed request); move to the next provider instead.
"""

from __future__ import annotations


class AIError(Exception):
    """Base class for every error raised by ai_platform."""


class LLMError(AIError):
    """A call to an LLM provider failed."""

    retryable: bool = False

    def __init__(self, message: str, *, provider: str | None = None, model: str | None = None):
        super().__init__(message)
        self.provider = provider
        self.model = model

    def __str__(self) -> str:
        origin = "/".join(part for part in (self.provider, self.model) if part)
        base = super().__str__()
        return f"[{origin}] {base}" if origin else base


class LLMTimeoutError(LLMError):
    """The provider did not answer within the configured deadline."""

    retryable = True


class LLMRateLimitError(LLMError):
    """The provider throttled us (HTTP 429). ``retry_after`` is in seconds, if known."""

    retryable = True

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class LLMUnavailableError(LLMError):
    """Transient provider-side failure: connection error or 5xx."""

    retryable = True


class LLMAuthError(LLMError):
    """Credentials are missing, invalid, or lack permission."""


class LLMBadRequestError(LLMError):
    """The provider rejected the request itself (unknown model, invalid payload)."""


class CircuitOpenError(AIError):
    """The circuit breaker for a provider is open; the call was not attempted."""


class AllProvidersFailedError(AIError):
    """Every provider in the fallback chain failed or was skipped."""

    def __init__(self, errors: list[Exception]):
        self.errors = errors
        detail = "; ".join(str(err) for err in errors) or "no providers configured"
        super().__init__(f"All LLM providers failed: {detail}")


class OutputParseError(AIError):
    """The model output could not be parsed as the expected format (e.g. JSON)."""


class OutputValidationError(AIError):
    """The model output was parsed but violates the expected schema or rules."""


def is_retryable(exc: BaseException) -> bool:
    """True when retrying the same call has a reasonable chance of succeeding."""
    return bool(getattr(exc, "retryable", False))
