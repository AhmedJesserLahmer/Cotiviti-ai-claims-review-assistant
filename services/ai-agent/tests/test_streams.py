import json

import pytest

pytest.importorskip("langgraph")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from agent import graph  # noqa: E402
from routers import streams  # noqa: E402
from tests.test_analyses_api import SIGNALS, FakeCollection, FakeDB  # noqa: E402


def parse(body: str):
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def test_stream_analysis_emits_every_stage_then_result(monkeypatch):
    async def fetch(state):
        return {**state, "claim": {}, "patient": {}, "provider": {}, "timeseries_window": [{}] * 30}

    async def ml(state):
        return {**state, "signals": SIGNALS}

    async def reason(state):
        return {**state, "reasoning": "1. fine"}

    async def recommend(state):
        return {**state, "recommendation": "approve", "recommendation_summary": "ok"}

    async def persist(state):
        return state

    for name, fn in [("fetch_claim_context", fetch), ("run_ml_signals", ml), ("reasoning_node", reason),
                     ("recommendation_node", recommend), ("persist_result", persist)]:
        monkeypatch.setattr(graph, name, fn)
    monkeypatch.setattr(graph, "_compiled_graph", None)
    events = [e async for e in graph.stream_analysis("C1")]
    monkeypatch.setattr(graph, "_compiled_graph", None)

    stages = [payload["stage"] for kind, payload in events if kind == "stage"]
    assert stages == ["fetch_claim_context", "run_ml_signals", "reasoning_node", "recommendation_node", "persist_result"]
    assert events[0][1]["timeseries_days"] == 30
    kind, result = events[-1]
    assert kind == "result" and result["recommendation"] == "approve" and "ai_metadata" in result


def test_sse_endpoint(monkeypatch):
    async def fake_stream(claim_id, bypass_cache=False):
        yield "stage", {"stage": "run_ml_signals"}
        yield "result", {"claim_id": claim_id}

    monkeypatch.setattr(streams, "db", FakeDB(claims=FakeCollection({"claim_id": "C1"})))
    monkeypatch.setattr(streams, "stream_analysis", fake_stream)
    response = TestClient(main.app).get("/v1/analyses/C1/stream")
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [e for e, _ in parse(response.text)] == ["start", "stage", "result"]


def test_sse_errors_end_the_stream_cleanly(monkeypatch):
    async def failing(claim_id, bypass_cache=False):
        raise graph.MLUnavailableError("down")
        yield  # pragma: no cover

    monkeypatch.setattr(streams, "db", FakeDB(claims=FakeCollection({"claim_id": "C1"})))
    monkeypatch.setattr(streams, "stream_analysis", failing)
    events = parse(TestClient(main.app).get("/v1/analyses/C1/stream").text)
    assert events[-1] == ("error", {"detail": "ML scoring is temporarily unavailable", "status": 503})


def test_unknown_claim_is_404(monkeypatch):
    monkeypatch.setattr(streams, "db", FakeDB(claims=FakeCollection(None)))
    assert TestClient(main.app).get("/v1/analyses/X/stream").status_code == 404
