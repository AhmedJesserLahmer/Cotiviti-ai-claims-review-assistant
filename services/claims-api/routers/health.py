"""Readiness checks for claims-api (probe routes come from claims_common.health).

Only MongoDB gates readiness. The ai-agent is reported for information: when it is
down, browsing claims still works and analyze calls return 503 with a clear message.
"""

from core.clients import get_ai_agent, get_ml_service
from db.mongo import db


async def mongo_ping() -> None:
    await db.command("ping")


READINESS_CHECKS = {"mongo": mongo_ping}


def dependency_info() -> dict:
    return {"dependencies": [get_ai_agent().snapshot(), get_ml_service().snapshot()]}
