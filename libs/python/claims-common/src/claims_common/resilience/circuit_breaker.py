"""Per-provider circuit breaker.

CLOSED     normal operation; consecutive failures are counted.
OPEN       after ``failure_threshold`` consecutive failures calls are rejected without
           touching the provider, so a dead model costs ~0 ms instead of a full timeout.
HALF_OPEN  after ``recovery_timeout_s`` a limited number of trial calls are let through;
           a success closes the circuit, a failure opens it again.

The breaker lives in process memory: each replica protects itself. That is the usual
trade-off for LLM calls, where a shared store would add a dependency on the hot path.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 30.0,
        half_open_max_calls: int = 1,
        clock: Callable[[], float] = time.monotonic,
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.half_open_max_calls = half_open_max_calls
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = 0.0
        self._half_open_in_flight = 0

    @property
    def state(self) -> CircuitState:
        if (
            self._state is CircuitState.OPEN
            and self._clock() - self._opened_at >= self.recovery_timeout_s
        ):
            self._state = CircuitState.HALF_OPEN
            self._half_open_in_flight = 0
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def allow_request(self) -> bool:
        state = self.state
        if state is CircuitState.CLOSED:
            return True
        if state is CircuitState.HALF_OPEN and self._half_open_in_flight < self.half_open_max_calls:
            self._half_open_in_flight += 1
            return True
        return False

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._half_open_in_flight = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self.state is CircuitState.HALF_OPEN or self._consecutive_failures >= self.failure_threshold:
            self._trip()

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self._consecutive_failures,
        }

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._half_open_in_flight = 0
