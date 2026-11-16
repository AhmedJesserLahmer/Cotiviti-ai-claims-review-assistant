from fastapi import APIRouter

from data_gen.seed_mongo import seed
from models.schemas import SeedResponse

router = APIRouter(tags=["seed"])


@router.post("/seed", response_model=SeedResponse)
async def seed_database():
    counts = await seed()
    return SeedResponse(status="ok", counts=counts)
