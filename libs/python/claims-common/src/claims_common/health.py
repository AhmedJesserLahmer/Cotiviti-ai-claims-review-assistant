"""Health probe router factory.

/health        legacy alias of liveness (compose healthchecks, old clients)
/health/live   the process answers; never checks dependencies
/health/ready  every registered readiness check passes (503 otherwise)

Readiness checks are ``async () -> None`` callables that raise on failure. ``info`` is
an optional callable whose result is attached to the readiness body (informational,
never affects the status code).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

ReadinessCheck = Callable[[], Awaitable[None]]


async def _run_check(check: ReadinessCheck, timeout_s: float) -> dict:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(check(), timeout=timeout_s)
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        return {"status": "down", "error": f"{type(exc).__name__}: {exc}"[:200]}
    return {"status": "up", "latency_ms": round((time.perf_counter() - started) * 1000, 1)}


def build_health_router(
    checks: dict[str, ReadinessCheck] | None = None,
    *,
    info: Callable[[], dict] | None = None,
    timeout_s: float = 2.0,
) -> APIRouter:
    router = APIRouter(tags=["health"])
    registered = dict(checks or {})

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/health/live")
    async def liveness():
        return {"status": "alive"}

    @router.get("/health/ready")
    async def readiness():
        names = list(registered)
        results = await asyncio.gather(*(_run_check(registered[n], timeout_s) for n in names))
        report = dict(zip(names, results, strict=True))
        ready = all(r["status"] == "up" for r in results)
        body: dict = {"status": "ready" if ready else "not_ready", "checks": report}
        if info is not None:
            try:
                body["info"] = info()
            except Exception as exc:  # noqa: BLE001 - informational only
                body["info"] = {"error": str(exc)[:200]}
        return JSONResponse(body, status_code=200 if ready else 503)

    return router
