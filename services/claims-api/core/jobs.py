"""Asynchronous analysis jobs.

A job analyzes a batch of claims through ai-agent and records per-claim results in
the ``analysis_jobs`` collection, so progress survives restarts and is visible to
every replica. How a job is executed is pluggable:

* ``InProcessRunner``  asyncio task in this process (default, no extra infrastructure)
* ``ArqRunner``        Redis queue consumed by the worker deployment (see core/worker.py)

Per-claim failures never fail the whole job; they are recorded and counted.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from fastapi import HTTPException
from prometheus_client import Counter

from core.analysis import request_analysis
from core.config import settings

log = logging.getLogger("claims_api.jobs")

JOBS_FINISHED = Counter("analysis_jobs_total", "Finished analysis jobs", ["status"])
JOB_CLAIMS = Counter("analysis_job_claims_total", "Claims processed by jobs", ["outcome"])

JobStatus = Literal["queued", "running", "completed", "completed_with_errors", "failed"]
COLLECTION = "analysis_jobs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, db):
        self.collection = db[COLLECTION]

    async def create(self, claim_ids: list[str], *, source: str) -> dict[str, Any]:
        job = {
            "job_id": f"job_{uuid.uuid4().hex[:16]}",
            "status": "queued",
            "source": source,
            "claim_ids": claim_ids,
            "total": len(claim_ids),
            "succeeded": 0,
            "failed": 0,
            "results": [],
            "created_at": _now(),
            "updated_at": _now(),
        }
        await self.collection.insert_one(dict(job))
        return job

    async def get(self, job_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"job_id": job_id}, {"_id": 0})

    async def mark(self, job_id: str, status: JobStatus, **fields) -> None:
        await self.collection.update_one(
            {"job_id": job_id}, {"$set": {"status": status, "updated_at": _now(), **fields}}
        )

    async def record(self, job_id: str, result: dict[str, Any], *, ok: bool) -> None:
        JOB_CLAIMS.labels("ok" if ok else "error").inc()
        await self.collection.update_one(
            {"job_id": job_id},
            {
                "$push": {"results": result},
                "$inc": {"succeeded" if ok else "failed": 1},
                "$set": {"updated_at": _now()},
            },
        )


async def run_job(store: JobStore, job_id: str, *, concurrency: int | None = None) -> None:
    job = await store.get(job_id)
    if job is None:
        log.error("job not found", extra={"job_id": job_id})
        return
    await store.mark(job_id, "running", started_at=_now())
    semaphore = asyncio.Semaphore(concurrency or settings.analysis_concurrency)

    async def analyze_one(claim_id: str) -> None:
        async with semaphore:
            try:
                result = await request_analysis(claim_id)
            except HTTPException as exc:
                await store.record(job_id, {"claim_id": claim_id, "error": str(exc.detail)}, ok=False)
                return
            except Exception as exc:  # noqa: BLE001 - one claim must not kill the batch
                log.exception("unexpected analysis failure", extra={"job_id": job_id, "claim_id": claim_id})
                await store.record(job_id, {"claim_id": claim_id, "error": type(exc).__name__}, ok=False)
                return
            await store.record(
                job_id,
                {
                    "claim_id": claim_id,
                    "recommendation": result.recommendation,
                    "decision_source": (result.ai_metadata or {}).get("decision_source"),
                },
                ok=True,
            )

    try:
        await asyncio.gather(*(analyze_one(cid) for cid in job["claim_ids"]))
    except Exception as exc:  # noqa: BLE001
        await store.mark(job_id, "failed", error=str(exc)[:300], finished_at=_now())
        raise
    final = await store.get(job_id) or {}
    status: JobStatus = "completed" if not final.get("failed") else "completed_with_errors"
    await store.mark(job_id, status, finished_at=_now())
    JOBS_FINISHED.labels(status).inc()
    log.info("job finished", extra={"job_id": job_id, "status": status, "total": job["total"],
                                    "failed": final.get("failed", 0)})


class JobRunner(Protocol):
    name: str

    async def enqueue(self, job_id: str) -> None: ...


class InProcessRunner:
    """Runs jobs as asyncio tasks of this process. Jobs in flight are lost on restart
    (they stay 'running' in the store); use the Redis runner in production."""

    name = "in-process"

    def __init__(self, store: JobStore):
        self.store = store
        self._tasks: set[asyncio.Task] = set()

    async def enqueue(self, job_id: str) -> None:
        task = asyncio.create_task(run_job(self.store, job_id))
        self._tasks.add(task)  # keep a reference so the task is not garbage-collected
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)


class ArqRunner:
    """Queues jobs in Redis for the arq worker (core/worker.py)."""

    name = "redis"

    def __init__(self, redis_url: str, *, pool_factory=None):
        self.redis_url = redis_url
        self._pool = None
        self._pool_factory = pool_factory

    async def _get_pool(self):
        if self._pool is None:
            if self._pool_factory is not None:
                self._pool = await self._pool_factory()
            else:
                from arq import create_pool
                from arq.connections import RedisSettings

                self._pool = await create_pool(RedisSettings.from_dsn(self.redis_url))
        return self._pool

    async def enqueue(self, job_id: str) -> None:
        pool = await self._get_pool()
        # _job_id makes enqueueing idempotent: retries never run the same job twice.
        await pool.enqueue_job("analyze_job", job_id, _job_id=job_id)

    async def aclose(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
