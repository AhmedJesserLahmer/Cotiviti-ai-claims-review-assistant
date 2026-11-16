"""Internal analysis API consumed by claims-api and the worker."""

from fastapi import APIRouter, HTTPException

from agent.graph import analyze_claim
from ai_platform.service import get_claim_review_ai
from claims_common.contracts import AnalysisRequest, AnalysisResult, SeedResponse
from data_gen.seed_mongo import seed
from db.mongo import db

router = APIRouter(prefix="/v1", tags=["analyses"])


@router.post("/analyses", response_model=AnalysisResult)
async def create_analysis(body: AnalysisRequest):
    claim = await db["claims"].find_one({"claim_id": body.claim_id}, {"_id": 0, "claim_id": 1})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return await analyze_claim(body.claim_id)


@router.get("/analyses/{claim_id}", response_model=AnalysisResult)
async def get_analysis(claim_id: str):
    analysis = await db["claim_analyses"].find_one({"claim_id": claim_id}, {"_id": 0})
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this claim yet")
    return analysis


@router.post("/seed", response_model=SeedResponse)
async def seed_database():
    return SeedResponse(status="ok", counts=await seed())


@router.get("/ai/status")
async def ai_status():
    return get_claim_review_ai().health()
