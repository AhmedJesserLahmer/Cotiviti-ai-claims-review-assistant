from contextlib import asynccontextmanager

from claims_common.app import create_app
from core.clients import close_clients
from core.config import settings
from routers import claims, health, providers, seed


@asynccontextmanager
async def lifespan(_app):
    yield
    await close_clients()


app = create_app(
    settings,
    title="Claims Review Assistant API",
    version="0.3.0",
    readiness_checks=health.READINESS_CHECKS,
    health_info=health.dependency_info,
    lifespan=lifespan,
)

app.include_router(seed.router)
app.include_router(claims.router)
app.include_router(providers.router)
