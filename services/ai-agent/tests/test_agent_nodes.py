"""LangGraph nodes delegate LLM work to ClaimReviewAI (needs the full service deps)."""

import httpx
import pytest

pytest.importorskip("langgraph")
pytest.importorskip("motor")

from agent import graph  # noqa: E402
from ai_platform.client import ResilientLLMClient  # noqa: E402
from ai_platform.config import AISettings  # noqa: E402
from ai_platform.providers.scripted import ScriptedProvider  # noqa: E402
from ai_platform.service import ClaimReviewAI  # noqa: E402
from claims_common.http import ServiceClient  # noqa: E402

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


async def test_run_ml_signals_combines_ml_service_and_provider_context(monkeypatch):
    seen = {}

    def handler(request):
        seen["body"] = request.read()
        return httpx.Response(200, json={
            "predicted_risk_label": "Medium", "risk_probabilities": {"Low": 0.3, "Medium": 0.6, "High": 0.1},
            "predicted_paid_amount": 812.5, "model_version": "v1",
        })

    client = ServiceClient("ml-service", "http://ml", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(graph, "get_ml_service", lambda: client)
    state = {
        "claim": {"billed_amount": 1000.0, "treatment_type": "Outpatient", "procedure_code": "CPT10001",
                  "length_of_stay": 0, "prior_claims_count": 1},
        "patient": {"age": 40},
        "provider": {"avg_claim_amount": 950.0, "cluster_id": 2, "cluster_label": "Standard"},
        "timeseries_window": [{"is_anomaly": True, "anomaly_score": 0.7}, {"is_anomaly": False, "anomaly_score": 0.41}],
    }
    signals = (await graph.run_ml_signals(state))["signals"]
    assert signals["predicted_risk_label"] == "Medium" and signals["predicted_paid_amount"] == 812.5
    assert signals["anomaly_flagged_days"] == 1 and signals["is_recent_anomaly"] is False
    assert b'"patient_age":40' in seen["body"].replace(b" ", b"")
