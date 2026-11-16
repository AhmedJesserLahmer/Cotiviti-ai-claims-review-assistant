from claims_common.app import create_app
from core.config import settings
from routers import claims, health, providers, seed

app = create_app(
    settings,
    title="Claims Review Assistant API",
    version="0.2.0",
    readiness_checks=health.READINESS_CHECKS,
    health_info=health.ai_info,
)

app.include_router(seed.router)
app.include_router(claims.router)
app.include_router(providers.router)
