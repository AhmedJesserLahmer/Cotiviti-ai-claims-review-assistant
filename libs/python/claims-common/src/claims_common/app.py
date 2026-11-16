"""FastAPI application factory used by every service.

Gives each service the same baseline: JSON logging, request-id propagation, CORS from
settings, and health probes. Services add their own routers on top.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from claims_common.health import ReadinessCheck, build_health_router
from claims_common.logging import RequestContextMiddleware, configure_logging
from claims_common.metrics import MetricsMiddleware, render_latest
from claims_common.settings import ServiceSettings
from claims_common.tracing import setup_tracing


def create_app(
    settings: ServiceSettings,
    *,
    title: str,
    version: str = "0.1.0",
    readiness_checks: dict[str, ReadinessCheck] | None = None,
    health_info: Callable[[], dict] | None = None,
    cors: bool = True,
    **fastapi_kwargs,
) -> FastAPI:
    configure_logging(settings.log_level, settings.log_format)
    app = FastAPI(
        title=title,
        version=version,
        # Interactive docs are handy locally but are attack surface in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        **fastapi_kwargs,
    )
    if cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )
    app.add_middleware(MetricsMiddleware, service=settings.service_name)
    # Added last so it wraps everything, including CORS preflight responses.
    app.add_middleware(RequestContextMiddleware)
    app.include_router(build_health_router(readiness_checks, info=health_info))

    if settings.metrics_enabled:
        # Prometheus scrape endpoint. Metrics are per process: run one uvicorn worker per
        # container and scale with replicas so every scrape sees the whole process.
        @app.get("/metrics", include_in_schema=False)
        async def metrics() -> Response:
            body, content_type = render_latest()
            return Response(content=body, media_type=content_type)

    app.state.settings = settings
    app.state.tracing = setup_tracing(app, settings.service_name)
    return app
