"""Prometheus metrics shared by every service.

``MetricsMiddleware`` records RED metrics (rate, errors, duration) per route
*template* (``/claims/{claim_id}``, never the raw path, to keep label cardinality
bounded). Services define their domain metrics with the helpers below; all metrics
live in the default registry exposed at ``/metrics``.
"""

from __future__ import annotations

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP requests handled", ["service", "method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["service", "method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
HTTP_IN_FLIGHT = Gauge("http_requests_in_flight", "HTTP requests being handled", ["service"])
RATE_LIMITED = Counter("rate_limit_rejections_total", "Requests rejected by the rate limiter", ["service", "rule"])

_UNMATCHED = "__unmatched__"


class MetricsMiddleware:
    def __init__(self, app, service: str):
        self.app = app
        self.service = service

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") == "/metrics":
            await self.app(scope, receive, send)
            return
        status = {"code": 500}
        started = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        HTTP_IN_FLIGHT.labels(self.service).inc()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            HTTP_IN_FLIGHT.labels(self.service).dec()
            route = scope.get("route")
            template = getattr(route, "path", None) or _UNMATCHED
            method = scope.get("method", "GET")
            HTTP_REQUESTS.labels(self.service, method, template, str(status["code"])).inc()
            HTTP_LATENCY.labels(self.service, method, template).observe(time.perf_counter() - started)


def render_latest() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
