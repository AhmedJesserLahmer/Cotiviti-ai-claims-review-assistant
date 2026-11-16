from contextlib import asynccontextmanager

from fastapi import Depends

from claims_common.app import create_app
from core.clients import close_clients
from core.config import settings
from core.runners import close_runner
from core.security import admin, reviewer
from routers import claims, feedback, health, jobs, providers, seed


@asynccontextmanager
async def lifespan(_app):
    yield
    await close_runner()
    await close_clients()


app = create_app(
    settings,
    title="Claims Review Assistant API",
    version="0.3.0",
    readiness_checks=health.READINESS_CHECKS,
    health_info=health.dependency_info,
    lifespan=lifespan,
)

# Every business route needs a valid bearer token with the right role when
# AUTH_ENABLED=true; probes and /metrics stay open (protected at the network level).
app.include_router(seed.router, dependencies=[Depends(admin)])
for router in (claims.router, providers.router, jobs.router, feedback.router):
    app.include_router(router, dependencies=[Depends(reviewer)])
