import pytest
from fastapi.testclient import TestClient

from claims_common.app import create_app
from claims_common.settings import ServiceSettings


async def ok():
    return None


async def broken():
    raise ConnectionError("db down")


def make(checks, **settings):
    app = create_app(ServiceSettings(_env_file=None, **settings), title="t", readiness_checks=checks,
                     health_info=lambda: {"mode": "x"})
    return TestClient(app)


def test_probes_ready():
    c = make({"db": ok})
    assert c.get("/health/live").json() == {"status": "alive"}
    r = c.get("/health/ready")
    assert r.status_code == 200 and r.json()["checks"]["db"]["status"] == "up"
    assert r.json()["info"] == {"mode": "x"}
    assert "x-request-id" in r.headers


def test_probes_not_ready():
    r = make({"db": ok, "cache": broken}).get("/health/ready")
    assert r.status_code == 503
    assert r.json()["checks"]["cache"]["error"].startswith("ConnectionError")


def test_docs_disabled_in_production():
    assert make({}, environment="prod").get("/docs").status_code == 404
    assert make({}).get("/docs").status_code == 200


def test_cors_rules(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example/, http://localhost:3000")
    assert ServiceSettings(_env_file=None).cors_origin_list == ["https://a.example", "http://localhost:3000"]
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValueError):
        ServiceSettings(_env_file=None).cors_origin_list
