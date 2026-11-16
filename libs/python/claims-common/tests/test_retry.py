import pytest

from claims_common.resilience.retry import RetryPolicy, is_retryable, retry_async


class Transient(Exception):
    retryable = True


class Fatal(Exception):
    pass


async def _no_sleep(_):
    return None


async def test_generic_errors_opt_in_to_retries():
    calls = []

    async def fn():
        calls.append(1)
        if len(calls) < 3:
            raise Transient()
        return "ok"

    assert await retry_async(fn, RetryPolicy(max_attempts=3), sleep=_no_sleep) == "ok"
    assert is_retryable(Transient()) and not is_retryable(Fatal())


async def test_fatal_errors_are_not_retried():
    calls = []

    async def fn():
        calls.append(1)
        raise Fatal()

    with pytest.raises(Fatal):
        await retry_async(fn, RetryPolicy(max_attempts=5), sleep=_no_sleep)
    assert len(calls) == 1
