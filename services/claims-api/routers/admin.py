"""Administrative endpoints (admin role)."""

from fastapi import APIRouter

from core.audit import get_audit_log

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit/verify")
async def verify_audit_log():
    """Check every audit entry's signature and that no sequence number is missing."""
    return (await get_audit_log().verify()).as_dict()
