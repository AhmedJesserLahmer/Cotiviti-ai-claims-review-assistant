"""ai-agent: runs the LangGraph claim-review agent behind an internal API.

Internal service: it is only called by claims-api (and the worker), never by browsers,
so CORS is disabled.
"""

from ai_platform.service import get_claim_review_ai
from claims_common.app import create_app
from core.config import settings
from routers import analyses, health

app = create_app(
    settings,
    title="Claims Review AI Agent",
    version="0.1.0",
    readiness_checks=health.READINESS_CHECKS,
    health_info=lambda: {"ai": get_claim_review_ai().health()},
    cors=False,
)

app.include_router(analyses.router)
