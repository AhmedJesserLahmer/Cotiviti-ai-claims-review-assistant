"""arq worker that executes analysis jobs from Redis.

Run with: arq core.worker.WorkerSettings
Deployed as its own container/Deployment so bulk analyses scale independently of
the API and survive API restarts.
"""

from __future__ import annotations

from arq.connections import RedisSettings

from claims_common.logging import configure_logging
from core.clients import close_clients
from core.config import settings
from core.jobs import JobStore, run_job
from db.mongo import db

TASK_NAME = "analyze_job"


async def analyze_job(ctx, job_id: str) -> None:
    await run_job(JobStore(db), job_id)


async def startup(ctx) -> None:
    configure_logging(settings.log_level, settings.log_format)


async def shutdown(ctx) -> None:
    await close_clients()


class WorkerSettings:
    functions = [analyze_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url or "redis://localhost:6379")
    # One job already fans out to `analysis_concurrency` parallel analyses.
    max_jobs = 2
    job_timeout = 60 * 60
    keep_result = 24 * 60 * 60
