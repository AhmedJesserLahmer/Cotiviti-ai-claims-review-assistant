import time

import pytest

pytest.importorskip("motor")
jwt = pytest.importorskip("jwt")

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core import security  # noqa: E402

SECRET = "k" * 40


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setattr(security.auth_settings, "auth_enabled", True)
    monkeypatch.setattr(security.auth_settings, "jwt_secret", SECRET)
    return TestClient(main.app)


def test_business_routes_require_a_token(auth_on):
    assert auth_on.get("/claims").status_code == 401
    assert auth_on.post("/claims/C1/analyze").status_code == 401
    assert auth_on.get("/analytics/ai-quality").status_code == 401


def test_probes_and_metrics_stay_open(auth_on):
    assert auth_on.get("/health/live").status_code == 200
    assert auth_on.get("/metrics").status_code == 200


def test_valid_token_passes_authentication(auth_on, monkeypatch):
    from routers import providers

    class Empty:
        def find(self, *a, **k):
            from tests.fakes import FakeCursor

            return FakeCursor([])

    monkeypatch.setattr(providers, "db", {"providers": Empty()})
    token = jwt.encode({"sub": "rev-7", "exp": int(time.time()) + 60, "roles": ["reviewer"]}, SECRET, algorithm="HS256")
    assert auth_on.get("/providers", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def _token(sub, roles):
    return jwt.encode({"sub": sub, "exp": int(time.time()) + 60, "roles": roles}, SECRET, algorithm="HS256")


def test_role_checks(auth_on):
    reviewer = {"Authorization": f"Bearer {_token('rev-1', ['reviewer'])}"}
    nobody = {"Authorization": f"Bearer {_token('x', ['guest'])}"}
    assert auth_on.post("/seed", headers=reviewer).status_code == 403
    assert auth_on.get("/claims", headers=nobody).status_code == 403


def test_feedback_reviewer_comes_from_the_token(auth_on, monkeypatch):
    from routers import feedback
    from tests.fakes import FakeCollection, FakeDB

    analyses = FakeCollection([{"claim_id": "C1", "recommendation": "approve", "ai_metadata": {}}])
    monkeypatch.setattr(feedback, "db", FakeDB(claim_analyses=analyses, claim_feedback=FakeCollection()))
    headers = {"Authorization": f"Bearer {_token('real-reviewer', ['reviewer'])}"}
    body = {"verdict": "agree", "final_decision": "approve", "reviewer": "someone-else"}
    saved = auth_on.post("/claims/C1/feedback", json=body, headers=headers).json()
    assert saved["reviewer"] == "real-reviewer"
