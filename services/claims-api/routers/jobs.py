"""Asynchronous analysis jobs API."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.audit import get_audit_log
from core.config import settings
from core.limits import bulk_limit
from core.runners import get_job_runner, get_job_store
from core.security import Principal, get_principal
from db.mongo import db

router = APIRouter(prefix="/jobs", tags=["jobs"])


class AnalysisJobRequest(BaseModel):
    claim_ids: list[str] = Field(min_length=1)


async def start_analysis_job(claim_ids: list[str], *, source: str, actor: str = "anonymous") -> dict:
    if len(claim_ids) > settings.max_job_claims:
        raise HTTPException(status_code=413, detail=f"at most {settings.max_job_claims} claims per job")
    job = await get_job_store().create(claim_ids, source=source)
    await get_job_runner().enqueue(job["job_id"])
    await get_audit_log().append(
        "job.created", actor=actor, subject=job["job_id"], data={"claims": len(claim_ids), "source": source}
    )
    return job


@router.post("/analyses", status_code=202, dependencies=[bulk_limit])
async def create_analysis_job(body: AnalysisJobRequest, principal: Principal = Depends(get_principal)):
    unique_ids = list(dict.fromkeys(body.claim_ids))
    known = {doc["claim_id"] async for doc in db["claims"].find({"claim_id": {"$in": unique_ids}}, {"claim_id": 1})}
    missing = [cid for cid in unique_ids if cid not in known]
    if missing:
        raise HTTPException(status_code=404, detail=f"unknown claim_id(s): {', '.join(missing[:10])}")
    job = await start_analysis_job(unique_ids, source="api", actor=principal.subject)
    return JSONResponse(
        {"job_id": job["job_id"], "status": job["status"], "total": job["total"]},
        status_code=202,
        headers={"Location": f"/jobs/{job['job_id']}"},
    )


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = await get_job_store().get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    done = job.get("succeeded", 0) + job.get("failed", 0)
    job["progress"] = round(done / job["total"], 3) if job.get("total") else 1.0
    return job
