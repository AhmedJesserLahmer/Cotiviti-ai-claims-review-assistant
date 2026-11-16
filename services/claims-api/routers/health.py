"""Readiness checks for claims-api (probe routes come from claims_common.health).

The AI status is informational: an LLM outage degrades analyses to the rule engine,
so it must never make the API unready.
"""

from ai_platform.service import get_claim_review_ai
from db.mongo import db


async def mongo_ping() -> None:
    await db.command("ping")


READINESS_CHECKS = {"mongo": mongo_ping}


def ai_info() -> dict:
    return {"ai": get_claim_review_ai().health()}
