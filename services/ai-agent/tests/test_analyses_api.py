import pytest

pytest.importorskip("langgraph")

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from routers import analyses  # noqa: E402

SIGNALS = {
    "predicted_risk_label": "Low", "risk_probabilities": {"Low": 0.9}, "predicted_paid_amount": 900.0,
    "provider_cluster_id": 1, "provider_cluster_label": "Standard", "anomaly_flagged_days": 0,
    "anomaly_recent_score": 0.3, "is_recent_anomaly": False,
}


class FakeCollection:
    def __init__(self, doc):
        self.doc = doc

    async def find_one(self, *args, **kwargs):
        return self.doc


class FakeDB(dict):
    pass


def client(monkeypatch, claim=None, analysis=None):
    monkeypatch.setattr(analyses, "db", FakeDB(claims=FakeCollection(claim), claim_analyses=FakeCollection(analysis)))
    return TestClient(main.app)


def test_create_analysis_404_for_unknown_claim(monkeypatch):
    assert client(monkeypatch).post("/v1/analyses", json={"claim_id": "NOPE"}).status_code == 404


def test_create_analysis_validates_body(monkeypatch):
    assert client(monkeypatch).post("/v1/analyses", json={"claim_id": ""}).status_code == 422


def test_create_analysis_runs_agent(monkeypatch):
    async def fake_analyze(claim_id, bypass_cache=False):
        return {"claim_id": claim_id, "signals": SIGNALS, "reasoning": "r", "recommendation": "approve",
                "recommendation_summary": "s", "loops": 0, "ai_metadata": {"decision_source": "rules"}}

    monkeypatch.setattr(analyses, "analyze_claim", fake_analyze)
    r = client(monkeypatch, claim={"claim_id": "C1"}).post("/v1/analyses", json={"claim_id": "C1"})
    assert r.status_code == 200 and r.json()["ai_metadata"]["decision_source"] == "rules"


def test_get_analysis(monkeypatch):
    assert client(monkeypatch).get("/v1/analyses/C1").status_code == 404
