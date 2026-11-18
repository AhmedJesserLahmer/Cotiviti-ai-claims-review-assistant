from contextlib import asynccontextmanager

from fastapi import Depends

from claims_common.app import create_app
from core.clients import close_clients
from core.config import settings
from core.runners import close_runner
from core.security import get_principal
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

# Every business route needs a valid bearer token when AUTH_ENABLED=true; probes and
# /metrics stay open (they are protected at the network level).
authenticated = [Depends(get_principal)]
app.include_router(seed.router, dependencies=authenticated)
app.include_router(claims.router, dependencies=authenticated)
app.include_router(providers.router, dependencies=authenticated)
app.include_router(jobs.router, dependencies=authenticated)
app.include_router(feedback.router, dependencies=authenticated)
