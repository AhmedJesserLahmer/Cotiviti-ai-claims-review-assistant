"""Readiness checks for ml-service (probe routes come from claims_common.health)."""

from db.mongo import db


async def mongo_ping() -> None:
    await db.command("ping")


READINESS_CHECKS = {"mongo": mongo_ping}
