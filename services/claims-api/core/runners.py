"""Selects the job runner for this process: Redis/arq when REDIS_URL is set, else in-process."""

from core.config import settings
from core.jobs import ArqRunner, InProcessRunner, JobRunner, JobStore
from db.mongo import db

_runner: JobRunner | None = None


def get_job_store() -> JobStore:
    return JobStore(db)


def get_job_runner() -> JobRunner:
    global _runner
    if _runner is None:
        _runner = ArqRunner(settings.redis_url) if settings.redis_url else InProcessRunner(get_job_store())
    return _runner


async def close_runner() -> None:
    global _runner
    if isinstance(_runner, ArqRunner):
        await _runner.aclose()
    _runner = None
