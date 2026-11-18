from fastapi.testclient import TestClient

from claims_common.app import create_app
from claims_common.settings import ServiceSettings


def test_api_responses_carry_security_headers():
    r = TestClient(create_app(ServiceSettings(_env_file=None), title="t")).get("/health/live")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["content-security-policy"].startswith("default-src 'none'")
    assert "strict-transport-security" not in r.headers


def test_hsts_in_production_and_docs_keep_working():
    prod = TestClient(create_app(ServiceSettings(_env_file=None, environment="prod"), title="t"))
    assert prod.get("/health/live").headers["strict-transport-security"].startswith("max-age=")
    docs = TestClient(create_app(ServiceSettings(_env_file=None), title="t")).get("/docs")
    assert docs.status_code == 200 and "content-security-policy" not in docs.headers
