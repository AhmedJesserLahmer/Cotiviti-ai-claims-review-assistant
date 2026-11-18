from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from claims_common.metrics import MetricsMiddleware


def _value(name, labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_requests_are_counted_by_route_template():
    app = FastAPI()

    @app.get("/claims/{claim_id}")
    async def claim(claim_id: str):
        return {"id": claim_id}

    app.add_middleware(MetricsMiddleware, service="test-svc")
    client = TestClient(app)
    labels = {"service": "test-svc", "method": "GET", "route": "/claims/{claim_id}", "status": "200"}
    before = _value("http_requests_total", labels)
    client.get("/claims/A1")
    client.get("/claims/B2")
    assert _value("http_requests_total", labels) == before + 2  # one series, not one per id
    client.get("/nope")
    assert _value("http_requests_total", {**labels, "route": "__unmatched__", "status": "404"}) >= 1
    assert _value("http_request_duration_seconds_count", {k: labels[k] for k in ("service", "method", "route")}) >= 2


def test_metrics_endpoint_is_exposed_by_the_app_factory():
    from claims_common.app import create_app
    from claims_common.settings import ServiceSettings

    client = TestClient(create_app(ServiceSettings(_env_file=None, service_name="factory-svc"), title="t"))
    client.get("/health/live")
    body = client.get("/metrics").text
    assert 'http_requests_total{method="GET",route="/health/live",service="factory-svc",status="200"}' in body
    disabled = create_app(ServiceSettings(_env_file=None, metrics_enabled=False), title="t")
    assert TestClient(disabled).get("/metrics").status_code == 404
