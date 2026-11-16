from fastapi import APIRouter, HTTPException

from db.mongo import db
from models.schemas import ProviderClusterOut, TimeseriesPoint

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
async def list_providers():
    cursor = db["providers"].find({}, {"_id": 0})
    return await cursor.to_list(length=200)


@router.get("/{provider_id}/timeseries", response_model=list[TimeseriesPoint])
async def get_timeseries(provider_id: str, days: int = 90):
    cursor = (
        db["provider_timeseries"]
        .find({"provider_id": provider_id}, {"_id": 0})
        .sort("date", -1)
        .limit(days)
    )
    rows = await cursor.to_list(length=days)
    rows.reverse()
    if not rows:
        raise HTTPException(status_code=404, detail="No timeseries data for this provider")
    return rows


@router.get("/{provider_id}/cluster", response_model=ProviderClusterOut)
async def get_cluster(provider_id: str):
    provider = await db["providers"].find_one({"provider_id": provider_id}, {"_id": 0})
    if not provider or "cluster_id" not in provider:
        raise HTTPException(status_code=404, detail="Provider or cluster info not found")
    return ProviderClusterOut(
        provider_id=provider["provider_id"],
        cluster_id=int(provider["cluster_id"]),
        cluster_label=provider["cluster_label"],
        avg_billed=provider["avg_billed"],
        claim_volume=int(provider["claim_volume"]),
        denial_rate=provider["denial_rate"],
        avg_length_of_stay=provider["avg_length_of_stay"],
    )
