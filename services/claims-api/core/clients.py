"""Clients for downstream services, created once per process."""

from claims_common.http import ServiceClient
from claims_common.internal_auth import internal_headers
from claims_common.resilience.retry import RetryPolicy
from core.config import settings

_ai_agent: ServiceClient | None = None
_ml_service: ServiceClient | None = None


def get_ai_agent() -> ServiceClient:
    global _ai_agent
    if _ai_agent is None:
        _ai_agent = ServiceClient(
            "ai-agent",
            settings.ai_agent_url,
            timeout_s=settings.ai_agent_timeout_s,
            # Analyses are expensive: retry only once on transport errors / 503.
            retry_policy=RetryPolicy(max_attempts=2, base_delay_s=0.5, max_delay_s=2.0),
            headers=internal_headers(settings.internal_token),
        )
    return _ai_agent


def get_ml_service() -> ServiceClient:
    global _ml_service
    if _ml_service is None:
        _ml_service = ServiceClient(
            "ml-service", settings.ml_service_url, timeout_s=120.0, headers=internal_headers(settings.internal_token)
        )
    return _ml_service


async def close_clients() -> None:
    global _ai_agent, _ml_service
    for client in (_ai_agent, _ml_service):
        if client is not None:
            await client.aclose()
    _ai_agent = _ml_service = None
