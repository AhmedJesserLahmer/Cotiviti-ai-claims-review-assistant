"""Resilient HTTP client for service-to-service calls.

Each downstream service (ml-service, ai-agent, ...) gets one ``ServiceClient``:

* a shared ``httpx.AsyncClient`` (connection pooling, per-call timeouts),
* retries with backoff + jitter for transport errors and 502/503/504,
* a circuit breaker so a dead dependency fails fast,
* the current ``X-Request-ID`` forwarded so logs correlate across services.

Errors are normalized into two types callers can act on:
``ServiceUnavailableError`` (dependency down, worth degrading) and
``ServiceResponseError`` (dependency answered with an error, usually a caller bug).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from claims_common.logging import request_id_var
from claims_common.resilience.circuit_breaker import CircuitBreaker
from claims_common.resilience.retry import RetryPolicy, SleepFn, retry_async

log = logging.getLogger("claims.http")

RETRYABLE_STATUS = frozenset({502, 503, 504})


class ServiceError(Exception):
    def __init__(self, service: str, message: str):
        super().__init__(f"[{service}] {message}")
        self.service = service


class ServiceUnavailableError(ServiceError):
    """Transport failure, timeout, open circuit, or retryable 5xx after all retries."""

    retryable = True


class ServiceResponseError(ServiceError):
    """The service answered with a non-retryable error status."""

    def __init__(self, service: str, status_code: int, detail: Any):
        super().__init__(service, f"HTTP {status_code}: {str(detail)[:300]}")
        self.status_code = status_code
        self.detail = detail


class ServiceClient:
    def __init__(
        self,
        name: str,
        base_url: str,
        *,
        timeout_s: float = 10.0,
        retry_policy: RetryPolicy | None = None,
        breaker: CircuitBreaker | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        headers: dict[str, str] | None = None,
        sleep: SleepFn | None = None,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.retry_policy = retry_policy or RetryPolicy(max_attempts=3, base_delay_s=0.2, max_delay_s=2.0)
        self.breaker = breaker or CircuitBreaker(name, failure_threshold=5, recovery_timeout_s=15.0)
        self._sleep = sleep
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_s, connect=min(3.0, timeout_s)),
            transport=transport,
            headers=headers,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def snapshot(self) -> dict:
        return {"service": self.name, "base_url": self.base_url, **self.breaker.snapshot()}

    async def request_json(self, method: str, path: str, *, timeout_s: float | None = None, **kwargs) -> Any:
        if not self.breaker.allow_request():
            raise ServiceUnavailableError(self.name, "circuit open")

        headers = dict(kwargs.pop("headers", None) or {})
        request_id = request_id_var.get()
        if request_id:
            headers.setdefault("X-Request-ID", request_id)
        if timeout_s is not None:
            kwargs["timeout"] = timeout_s

        async def call() -> httpx.Response:
            try:
                response = await self._client.request(method, path, headers=headers, **kwargs)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                raise ServiceUnavailableError(self.name, f"{type(exc).__name__}: {exc}") from exc
            if response.status_code in RETRYABLE_STATUS:
                raise ServiceUnavailableError(self.name, f"HTTP {response.status_code}")
            return response

        def on_retry(attempt: int, exc: BaseException, delay: float) -> None:
            log.warning("retrying service call", extra={
                "service": self.name, "path": path, "attempt": attempt, "delay_s": round(delay, 3), "error": str(exc),
            })

        retry_kwargs = {"sleep": self._sleep} if self._sleep else {}
        try:
            response = await retry_async(call, self.retry_policy, on_retry=on_retry, **retry_kwargs)
        except ServiceUnavailableError:
            self.breaker.record_failure()
            raise
        self.breaker.record_success()

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ServiceResponseError(self.name, response.status_code, detail)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def get(self, path: str, **kwargs) -> Any:
        return await self.request_json("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Any:
        return await self.request_json("POST", path, **kwargs)
