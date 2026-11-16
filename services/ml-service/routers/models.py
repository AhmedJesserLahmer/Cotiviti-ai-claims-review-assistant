"""Model registry endpoints."""

from fastapi import APIRouter, HTTPException

from ml import inference, registry

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("")
async def list_models():
    return {"active": inference.active_version(), "versions": registry.list_versions()}


@router.get("/active")
async def active_model():
    bundle = inference.get_bundle()
    return bundle.manifest


@router.post("/{version}/activate")
async def activate(version: str):
    """Point CURRENT at an existing version and hot-reload it (rollback / promote)."""
    try:
        registry.set_current(version)
        bundle = inference.reload_bundle(version)
    except (registry.ModelNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"active": bundle.version}
