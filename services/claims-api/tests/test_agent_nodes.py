"""LangGraph nodes delegate LLM work to ClaimReviewAI (needs the full service deps)."""

import os

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("motor")
if not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "ml", "models", "classifier.joblib")):
    pytest.skip("models not trained yet (run: python -m ml.train_models)", allow_module_level=True)

from agent import graph  # noqa: E402
from ai_platform.client import ResilientLLMClient  # noqa: E402
from ai_platform.config import AISettings  # noqa: E402
from ai_platform.providers.scripted import ScriptedProvider  # noqa: E402
from ai_platform.service import ClaimReviewAI  # noqa: E402

STATE = {
    "claim_id": "C1",
    "loops": 0,
    "claim": {"billed_amount": 1000.0, "status": "Pending"},
    "provider": {"name": "Acme Clinic"},
    "signals": {
        "predicted_risk_label": "Low", "risk_probabilities": {"Low": 0.9, "High": 0.02},
        "predicted_paid_amount": 900.0, "is_recent_anomaly": False, "anomaly_flagged_days": 0,
    },
}


def _use(monkeypatch, *script):
    ai = ClaimReviewAI(ResilientLLMClient([ScriptedProvider(list(script))]), AISettings(_env_file=None))
    monkeypatch.setattr(graph, "get_claim_review_ai", lambda: ai)


async def test_nodes_produce_decision_and_audit(monkeypatch):
    _use(monkeypatch, "1. fine", '{"recommendation": "approve", "summary": "ok"}')
    state = await graph.recommendation_node(await graph.reasoning_node(dict(STATE)))
    assert state["recommendation"] == "approve"
    assert state["ai_run"].decision_source == "llm"
    assert graph._route_after_recommendation(state) == "persist_result"


async def test_request_more_data_loops_once(monkeypatch):
    _use(monkeypatch, "1. unsure", '{"recommendation": "request_more_data", "summary": "need history"}')
    state = await graph.recommendation_node(await graph.reasoning_node(dict(STATE)))
    assert state["loops"] == 1
    assert graph._route_after_recommendation(state) == "fetch_claim_context"
