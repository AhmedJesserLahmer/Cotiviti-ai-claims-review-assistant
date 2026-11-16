from fastapi import APIRouter, HTTPException

from claims_common.contracts import SeedResponse
from claims_common.http import ServiceError
from core.clients import get_ml_service

router = APIRouter(tags=["seed"])


@router.post("/seed", response_model=SeedResponse)
async def seed_database():
    """Re-seed the synthetic dataset (owned by ml-service)."""
    try:
        return await get_ml_service().post("/v1/seed")
    except ServiceError as exc:
        raise HTTPException(status_code=503, detail=f"Seeding failed: {exc}") from exc
