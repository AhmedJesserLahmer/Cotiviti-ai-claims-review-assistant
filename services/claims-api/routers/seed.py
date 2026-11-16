from fastapi import APIRouter, Depends, HTTPException

from claims_common.contracts import SeedResponse
from claims_common.http import ServiceError
from core.audit import get_audit_log
from core.clients import get_ml_service
from core.security import Principal, get_principal

router = APIRouter(tags=["seed"])


@router.post("/seed", response_model=SeedResponse)
async def seed_database(principal: Principal = Depends(get_principal)):
    """Re-seed the synthetic dataset (owned by ml-service)."""
    try:
        result = await get_ml_service().post("/v1/seed")
    except ServiceError as exc:
        raise HTTPException(status_code=503, detail=f"Seeding failed: {exc}") from exc
    await get_audit_log().append("dataset.seed", actor=principal.subject, subject="dataset", data=result.get("counts", {}))
    return result
