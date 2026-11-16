"""OpenTelemetry tracing, enabled by configuration only.

Tracing is off unless ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set (standard OTel variable),
so local runs and tests need no collector. When on:

* every inbound FastAPI request and outbound httpx call gets a span, and the W3C
  ``traceparent`` header links claims-api -> ai-agent -> ml-service into one trace;
* code can add spans with ``span("name", attr=value)``, which is a no-op without OTel.

All OpenTelemetry imports are lazy so services run without the packages installed.
"""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Iterator
from typing import Any

log = logging.getLogger("claims.tracing")

_configured = False


def tracing_enabled() -> bool:
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")) and os.environ.get("OTEL_SDK_DISABLED") != "true"


def setup_tracing(app: Any, service_name: str, *, exporter: Any = None) -> bool:
    """Instrument ``app`` (FastAPI) and httpx. Returns True when tracing is active.

    ``exporter`` overrides the OTLP exporter (tests pass an in-memory one).
    """
    global _configured
    if exporter is None and not tracing_enabled():
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    except ImportError:
        log.warning("OTEL_EXPORTER_OTLP_ENDPOINT is set but opentelemetry is not installed; tracing disabled")
        return False

    if not _configured:
        provider = TracerProvider(resource=Resource.create({
            "service.name": service_name,
            "deployment.environment": os.environ.get("ENVIRONMENT", "local"),
        }))
        if exporter is None:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        else:
            provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        HTTPXClientInstrumentor().instrument()
        _configured = True

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    log.info("tracing enabled", extra={"service": service_name})
    return True


@contextlib.contextmanager
def span(name: str, **attributes: Any) -> Iterator[Any]:
    """Start a child span if OpenTelemetry is available, else do nothing."""
    try:
        from opentelemetry import trace
    except ImportError:
        yield None
        return
    with trace.get_tracer("claims").start_as_current_span(name) as current:
        for key, value in attributes.items():
            if value is not None:
                current.set_attribute(key, value)
        yield current


def set_span_attributes(**attributes: Any) -> None:
    try:
        from opentelemetry import trace
    except ImportError:
        return
    current = trace.get_current_span()
    for key, value in attributes.items():
        if value is not None:
            current.set_attribute(key, value)
