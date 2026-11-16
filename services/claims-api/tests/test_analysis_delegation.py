import httpx
import pytest

pytest.importorskip("motor")

from fastapi import HTTPException  # noqa: E402

from claims_common.http import ServiceClient  # noqa: E402
from claims_common.resilience.retry import RetryPolicy  # noqa: E402
from core import analysis  # noqa: E402

RESULT = {
    "claim_id": "C1",
    "signals": {
        "predicted_risk_label": "Low", "risk_probabilities": {"Low": 0.9}, "predicted_paid_amount": 900.0,
        "provider_cluster_id": 1, "provider_cluster_label": "Standard", "anomaly_flagged_days": 0,
        "anomaly_recent_score": 0.3, "is_recent_anomaly": False,
    },
    "reasoning": "r", "recommendation": "approve", "recommendation_summary": "s", "loops": 0,
    "ai_metadata": {"decision_source": "llm"},
}


async def _no_sleep(_):
    return None


def use(monkeypatch, handler):
    client = ServiceClient("ai-agent", "http://ai-agent", transport=httpx.MockTransport(handler),
                           retry_policy=RetryPolicy(max_attempts=2), sleep=_no_sleep)
    monkeypatch.setattr(analysis, "get_ai_agent", lambda: client)


async def test_successful_delegation(monkeypatch):
    use(monkeypatch, lambda request: httpx.Response(200, json=RESULT))
    result = await analysis.request_analysis("C1")
    assert result.recommendation == "approve" and result.ai_metadata["decision_source"] == "llm"


async def test_agent_down_maps_to_503(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    use(monkeypatch, handler)
    with pytest.raises(HTTPException) as info:
        await analysis.request_analysis("C1")
    assert info.value.status_code == 503


@pytest.mark.parametrize("upstream, expected", [(404, 404), (422, 422), (500, 502)])
async def test_agent_errors_are_mapped(monkeypatch, upstream, expected):
    use(monkeypatch, lambda request: httpx.Response(upstream, json={"detail": "x"}))
    with pytest.raises(HTTPException) as info:
        await analysis.request_analysis("C1")
    assert info.value.status_code == expected


async def test_stream_proxy_forwards_events_and_converts_failures(monkeypatch):
    use(monkeypatch, lambda request: httpx.Response(200, content=b"event: result\ndata: {}\n\n"))
    assert b"".join([c async for c in analysis.proxy_analysis_stream("C1")]) == b"event: result\ndata: {}\n\n"

    def down(request):
        raise httpx.ConnectError("refused")

    use(monkeypatch, down)
    body = b"".join([c async for c in analysis.proxy_analysis_stream("C1")])
    assert body.startswith(b"event: error") and b"503" in body
