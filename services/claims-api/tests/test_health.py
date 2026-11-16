import pytest

pytest.importorskip("fastapi")
pytest.importorskip("motor")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from routers import health  # noqa: E402


class FakeDB:
    def __init__(self, fail=False):
        self.fail = fail

    async def command(self, name):
        if self.fail:
            raise ConnectionError("mongo unreachable")
        return {"ok": 1}


class FakeAI:
    def health(self):
        return {"llm_enabled": False, "circuits": []}


def client(monkeypatch, *, fail=False):
    monkeypatch.setattr(health, "db", FakeDB(fail))
    monkeypatch.setattr(health, "get_claim_review_ai", lambda: FakeAI())
    app = FastAPI()
    app.include_router(health.router)
    return TestClient(app)


def test_liveness_and_legacy_health(monkeypatch):
    c = client(monkeypatch, fail=True)  # liveness ignores dependencies
    assert c.get("/health/live").json() == {"status": "alive"}
    assert c.get("/health").json() == {"status": "ok"}


def test_ready_when_mongo_up(monkeypatch):
    r = client(monkeypatch).get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["checks"]["mongo"]["status"] == "up"
    assert body["ai"]["llm_enabled"] is False  # LLM off does not make the API unready


def test_not_ready_when_mongo_down(monkeypatch):
    r = client(monkeypatch, fail=True).get("/health/ready")
    assert r.status_code == 503
    assert "unreachable" in r.json()["checks"]["mongo"]["error"]
