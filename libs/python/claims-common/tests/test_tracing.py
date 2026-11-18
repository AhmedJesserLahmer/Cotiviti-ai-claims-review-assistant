import pytest

pytest.importorskip("opentelemetry.sdk")

from fastapi.testclient import TestClient  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402

from claims_common import tracing  # noqa: E402
from claims_common.app import create_app  # noqa: E402
from claims_common.settings import ServiceSettings  # noqa: E402

EXPORTER = InMemorySpanExporter()


def test_disabled_without_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = create_app(ServiceSettings(_env_file=None), title="t")
    assert app.state.tracing is False


def test_requests_and_custom_spans_are_exported():
    app = create_app(ServiceSettings(_env_file=None, service_name="svc"), title="t")

    @app.get("/work")
    async def work():
        with tracing.span("unit.of.work", **{"claim.id": "C1", "skipped": None}):
            return {"ok": True}

    assert tracing.setup_tracing(app, "svc", exporter=EXPORTER)
    TestClient(app).get("/work")
    spans = {s.name: s for s in EXPORTER.get_finished_spans()}
    assert spans["unit.of.work"].attributes["claim.id"] == "C1"
    assert "skipped" not in spans["unit.of.work"].attributes
    assert any(name.startswith("GET /work") for name in spans)
    assert spans["unit.of.work"].resource.attributes["service.name"] == "svc"


def test_span_helper_is_safe_without_active_tracing():
    with tracing.span("noop", a=1) as current:
        assert current is not None or current is None
    tracing.set_span_attributes(a=1)
