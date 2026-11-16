import pytest

pytest.importorskip("motor")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from routers import feedback  # noqa: E402
from tests.fakes import FakeCollection, FakeDB  # noqa: E402

ANALYSES = [
    {"claim_id": "C1", "recommendation": "approve",
     "ai_metadata": {"run_id": "r1", "decision_source": "llm", "model_used": "m",
                     "prompt_versions": {"claim_reasoning": "2.1.0"}}},
    {"claim_id": "C2", "recommendation": "flag_for_review",
     "ai_metadata": {"run_id": "r2", "decision_source": "rules", "recommendation_overridden": True}},
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(feedback, "db", FakeDB(claim_analyses=FakeCollection(ANALYSES), claim_feedback=FakeCollection()))
    return TestClient(main.app)


def test_feedback_is_stored_with_ai_snapshot(client):
    r = client.post("/claims/C1/feedback", json={"verdict": "override", "final_decision": "deny", "reviewer": "rev-1"})
    assert r.status_code == 201
    body = r.json()
    assert body["ai_recommendation"] == "approve" and body["ai_run_id"] == "r1" and body["ai_decision_source"] == "llm"


def test_feedback_validation(client):
    assert client.post("/claims/NOPE/feedback", json={"verdict": "agree", "final_decision": "approve", "reviewer": "r"}).status_code == 404
    mismatch = client.post("/claims/C1/feedback", json={"verdict": "agree", "final_decision": "deny", "reviewer": "r"})
    assert mismatch.status_code == 422


def test_quality_analytics(client):
    client.post("/claims/C1/feedback", json={"verdict": "override", "final_decision": "deny", "reviewer": "a"})
    client.post("/claims/C2/feedback", json={"verdict": "agree", "final_decision": "flag_for_review", "reviewer": "b"})
    report = client.get("/analytics/ai-quality").json()
    assert report["analyses"]["total"] == 2 and report["analyses"]["rule_engine_rate"] == 0.5
    assert report["analyses"]["policy_override_rate"] == 0.5
    assert report["feedback"]["agreement_rate"] == 0.5
    assert report["feedback"]["unsafe_approval_rate"] == 1.0
    assert report["feedback"]["agreement_by_source"] == {"llm": 0.0, "rules": 1.0}
    assert report["feedback"]["agreement_by_prompt"] == {"claim_reasoning@2.1.0": {"rate": 0.0, "n": 1}}
