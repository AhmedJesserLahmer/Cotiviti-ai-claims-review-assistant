import pytest

from claims_common.resilience.circuit_breaker import CircuitBreaker, CircuitState


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make(threshold=3, recovery=10):
    clock = Clock()
    return CircuitBreaker("p", failure_threshold=threshold, recovery_timeout_s=recovery, clock=clock), clock


def test_opens_after_consecutive_failures():
    breaker, _ = make(threshold=3)
    for _ in range(2):
        breaker.record_failure()
    assert breaker.state is CircuitState.CLOSED
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    assert not breaker.allow_request()


def test_success_resets_failure_count():
    breaker, _ = make(threshold=2)
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert breaker.state is CircuitState.CLOSED


def test_half_open_allows_limited_trials_then_closes_on_success():
    breaker, clock = make(threshold=1, recovery=10)
    breaker.record_failure()
    clock.now = 10
    assert breaker.state is CircuitState.HALF_OPEN
    assert breaker.allow_request()
    assert not breaker.allow_request()  # only one trial in flight
    breaker.record_success()
    assert breaker.state is CircuitState.CLOSED
    assert breaker.allow_request()


def test_half_open_failure_reopens():
    breaker, clock = make(threshold=3, recovery=5)
    for _ in range(3):
        breaker.record_failure()
    clock.now = 5
    assert breaker.allow_request()
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    clock.now = 9
    assert not breaker.allow_request()


def test_snapshot_and_validation():
    breaker, _ = make()
    assert breaker.snapshot() == {"name": "p", "state": "closed", "consecutive_failures": 0}
    with pytest.raises(ValueError):
        CircuitBreaker("x", failure_threshold=0)
