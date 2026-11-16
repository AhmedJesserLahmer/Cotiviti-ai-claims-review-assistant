import pytest

from ai_platform.errors import LLMAuthError, LLMRateLimitError, LLMTimeoutError
from ai_platform.resilience.retry import RetryPolicy, retry_async


class Flaky:
    def __init__(self, failures):
        self.failures = list(failures)
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return "ok"


async def _no_sleep(_):
    return None


async def test_retries_until_success():
    fn = Flaky([LLMTimeoutError("t1"), LLMTimeoutError("t2")])
    seen = []
    result = await retry_async(
        fn, RetryPolicy(max_attempts=3), sleep=_no_sleep, on_retry=lambda a, e, d: seen.append(a)
    )
    assert result == "ok"
    assert fn.calls == 3
    assert seen == [1, 2]


async def test_gives_up_after_max_attempts():
    fn = Flaky([LLMTimeoutError("t")] * 5)
    with pytest.raises(LLMTimeoutError):
        await retry_async(fn, RetryPolicy(max_attempts=2), sleep=_no_sleep)
    assert fn.calls == 2


async def test_non_retryable_error_is_raised_immediately():
    fn = Flaky([LLMAuthError("bad key")])
    with pytest.raises(LLMAuthError):
        await retry_async(fn, RetryPolicy(max_attempts=5), sleep=_no_sleep)
    assert fn.calls == 1


async def test_retry_after_is_respected_but_capped():
    delays = []

    async def record(d):
        delays.append(d)

    fn = Flaky([LLMRateLimitError("429", retry_after=3), LLMRateLimitError("429", retry_after=60)])
    policy = RetryPolicy(max_attempts=3, base_delay_s=0.1, max_delay_s=5, jitter=False)
    await retry_async(fn, policy, sleep=record)
    assert delays == [3.0, 5.0]


def test_backoff_is_exponential_capped_and_jittered():
    policy = RetryPolicy(base_delay_s=1, max_delay_s=5, multiplier=2, jitter=False)
    assert [policy.backoff(n) for n in (1, 2, 3, 4)] == [1, 2, 4, 5]
    jittered = RetryPolicy(base_delay_s=1, max_delay_s=5, multiplier=2)
    assert jittered.backoff(3, rng=lambda: 0.5) == 2.0


def test_invalid_policy():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
