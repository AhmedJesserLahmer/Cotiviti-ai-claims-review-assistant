import httpx
import pytest

from claims_common.http import ServiceClient, ServiceResponseError, ServiceUnavailableError
from claims_common.logging import request_id_var
from claims_common.resilience.circuit_breaker import CircuitBreaker
from claims_common.resilience.retry import RetryPolicy


async def _no_sleep(_):
    return None


def make(handler, attempts=3, threshold=5):
    return ServiceClient(
        "svc", "http://svc", transport=httpx.MockTransport(handler), sleep=_no_sleep,
        retry_policy=RetryPolicy(max_attempts=attempts), breaker=CircuitBreaker("svc", failure_threshold=threshold),
    )


async def test_success_and_request_id_propagation():
    seen = {}

    def handler(request):
        seen["rid"] = request.headers.get("x-request-id")
        return httpx.Response(200, json={"ok": True})

    token = request_id_var.set("rid-42")
    try:
        assert await make(handler).post("/v1/x", json={"a": 1}) == {"ok": True}
    finally:
        request_id_var.reset(token)
    assert seen["rid"] == "rid-42"


async def test_retries_503_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json={"n": len(calls)})

    assert await make(handler).get("/x") == {"n": 3}


async def test_transport_errors_become_unavailable_and_open_circuit():
    def handler(request):
        raise httpx.ConnectError("refused")

    client = make(handler, attempts=2, threshold=1)
    with pytest.raises(ServiceUnavailableError):
        await client.get("/x")
    with pytest.raises(ServiceUnavailableError, match="circuit open"):
        await client.get("/x")


async def test_4xx_is_not_retried_and_carries_detail():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404, json={"detail": "Claim not found"})

    with pytest.raises(ServiceResponseError) as info:
        await make(handler).get("/x")
    assert info.value.status_code == 404 and info.value.detail == "Claim not found"
    assert len(calls) == 1


async def test_stream_bytes_passes_chunks_through():
    def handler(request):
        return httpx.Response(200, content=b"event: a\ndata: {}\n\n")

    chunks = [c async for c in make(handler).stream_bytes("GET", "/s")]
    assert b"".join(chunks) == b"event: a\ndata: {}\n\n"


async def test_stream_bytes_errors():
    with pytest.raises(ServiceResponseError):
        [c async for c in make(lambda r: httpx.Response(404, content=b"nope")).stream_bytes("GET", "/s")]

    def down(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ServiceUnavailableError):
        [c async for c in make(down).stream_bytes("GET", "/s")]
