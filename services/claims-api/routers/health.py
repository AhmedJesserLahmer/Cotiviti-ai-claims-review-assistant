"""Kubernetes-style health probes.

/health/live   process is up and the event loop answers; no dependencies checked, so a
               slow database never gets healthy pods restarted.
/health/ready  dependencies are reachable (MongoDB ping under a short deadline); a
               failing check returns 503 so the pod is taken out of load balancing.
               The AI section is informational: an LLM outage degrades to the rule
               engine, so it must never make the API unready.
/health        kept for backwards compatibility (compose healthchecks, smoke tests).
"""

import asyncio
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ai_platform.service import get_claim_review_ai
from db.mongo import db

router = APIRouter(tags=["health"])

READINESS_TIMEOUT_S = 2.0


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/live")
async def liveness():
    return {"status": "alive"}


async def _check_mongo() -> dict:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(db.command("ping"), timeout=READINESS_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        return {"status": "down", "error": f"{type(exc).__name__}: {exc}"[:200]}
    return {"status": "up", "latency_ms": round((time.perf_counter() - started) * 1000, 1)}


@router.get("/health/ready")
async def readiness():
    mongo = await _check_mongo()
    ready = mongo["status"] == "up"
    try:
        ai = get_claim_review_ai().health()
    except Exception as exc:  # noqa: BLE001 - AI status is informational only
        ai = {"error": str(exc)[:200]}
    body = {"status": "ready" if ready else "not_ready", "checks": {"mongo": mongo}, "ai": ai}
    return JSONResponse(body, status_code=200 if ready else 503)
