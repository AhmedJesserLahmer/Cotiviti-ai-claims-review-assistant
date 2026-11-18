import pytest

pytest.importorskip("motor")

import main  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from claims_common.contracts import AnalysisResult  # noqa: E402
from core import jobs, runners  # noqa: E402
from routers import jobs as jobs_router  # noqa: E402
from tests.fakes import FakeCollection, FakeDB  # noqa: E402

SIGNALS = {
    "predicted_risk_label": "Low", "risk_probabilities": {"Low": 0.9}, "predicted_paid_amount": 900.0,
    "provider_cluster_id": 1, "provider_cluster_label": "Standard", "anomaly_flagged_days": 0,
    "anomaly_recent_score": 0.3, "is_recent_anomaly": False,
}


async def fake_analysis(claim_id):
    if claim_id == "BAD":
        raise HTTPException(status_code=503, detail="AI agent is unavailable")
    return AnalysisResult(claim_id=claim_id, signals=SIGNALS, reasoning="r", recommendation="approve",
                          recommendation_summary="s", loops=0, ai_metadata={"decision_source": "rules"})


async def test_job_records_successes_and_failures(monkeypatch):
    monkeypatch.setattr(jobs, "request_analysis", fake_analysis)
    store = jobs.JobStore(FakeDB())
    job = await store.create(["C1", "BAD", "C2"], source="test")
    await jobs.run_job(store, job["job_id"], concurrency=2)
    done = await store.get(job["job_id"])
    assert done["status"] == "completed_with_errors"
    assert done["succeeded"] == 2 and done["failed"] == 1
    assert {r["claim_id"] for r in done["results"]} == {"C1", "C2", "BAD"}
    assert next(r for r in done["results"] if r["claim_id"] == "BAD")["error"] == "AI agent is unavailable"


async def test_clean_job_completes(monkeypatch):
    monkeypatch.setattr(jobs, "request_analysis", fake_analysis)
    store = jobs.JobStore(FakeDB())
    job = await store.create(["C1"], source="test")
    runner = jobs.InProcessRunner(store)
    await runner.enqueue(job["job_id"])
    await runner.drain()
    assert (await store.get(job["job_id"]))["status"] == "completed"


def test_jobs_api_validates_and_reports(monkeypatch):
    fake_db = FakeDB(claims=FakeCollection([{"claim_id": "C1"}]))
    store = jobs.JobStore(fake_db)

    class NoopRunner:
        name = "noop"

        async def enqueue(self, job_id):
            return None

    monkeypatch.setattr(jobs_router, "db", fake_db)
    monkeypatch.setattr(jobs_router, "get_job_store", lambda: store)
    monkeypatch.setattr(jobs_router, "get_job_runner", lambda: NoopRunner())
    client = TestClient(main.app)

    assert client.post("/jobs/analyses", json={"claim_ids": ["C1", "NOPE"]}).status_code == 404
    accepted = client.post("/jobs/analyses", json={"claim_ids": ["C1", "C1"]})
    assert accepted.status_code == 202 and accepted.headers["location"].startswith("/jobs/job_")
    status = client.get(accepted.headers["location"]).json()
    assert status["status"] == "queued" and status["total"] == 1 and status["progress"] == 0
    assert client.get("/jobs/job_missing").status_code == 404


def test_default_runner_is_in_process():
    assert runners.get_job_runner().name == "in-process"


async def test_arq_runner_enqueues_idempotently():
    calls = []

    class FakePool:
        async def enqueue_job(self, name, *args, **kwargs):
            calls.append((name, args, kwargs))

        async def aclose(self):
            calls.append("closed")

    async def factory():
        return FakePool()

    runner = jobs.ArqRunner("redis://x", pool_factory=factory)
    await runner.enqueue("job_1")
    await runner.aclose()
    assert calls[0] == ("analyze_job", ("job_1",), {"_job_id": "job_1"}) and calls[-1] == "closed"


def test_worker_settings_are_importable():
    pytest.importorskip("arq")
    from core import worker

    assert worker.WorkerSettings.functions == [worker.analyze_job]
    assert worker.TASK_NAME == "analyze_job"
