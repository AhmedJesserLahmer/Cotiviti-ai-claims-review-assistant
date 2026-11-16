"""Selects the job runner for this process."""

from core.jobs import InProcessRunner, JobRunner, JobStore
from db.mongo import db

_runner: JobRunner | None = None


def get_job_store() -> JobStore:
    return JobStore(db)


def get_job_runner() -> JobRunner:
    global _runner
    if _runner is None:
        _runner = InProcessRunner(get_job_store())
    return _runner
