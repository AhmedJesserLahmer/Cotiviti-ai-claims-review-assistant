"""ml-service: owns the synthetic dataset, model training and model inference.

Internal service (called by ai-agent and claims-api), so CORS is disabled.
"""

from claims_common.app import create_app
from core.config import settings
from routers import health

app = create_app(
    settings,
    title="Claims Review ML Service",
    version="0.1.0",
    readiness_checks=health.READINESS_CHECKS,
    cors=False,
)
