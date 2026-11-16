"""Clients for downstream services, created once per process."""

from claims_common.http import ServiceClient
from core.config import settings

_ml_service: ServiceClient | None = None


def get_ml_service() -> ServiceClient:
    global _ml_service
    if _ml_service is None:
        _ml_service = ServiceClient("ml-service", settings.ml_service_url, timeout_s=settings.ml_service_timeout_s)
    return _ml_service


async def close_clients() -> None:
    global _ml_service
    if _ml_service is not None:
        await _ml_service.aclose()
        _ml_service = None
