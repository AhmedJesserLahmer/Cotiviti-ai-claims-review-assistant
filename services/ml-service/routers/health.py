"""Readiness checks for ml-service (probe routes come from claims_common.health)."""

from db.mongo import db


async def mongo_ping() -> None:
    await db.command("ping")


async def model_loaded() -> None:
    # Raises ModelNotFoundError when no version is active, making the pod unready.
    from ml.inference import get_bundle

    get_bundle()


READINESS_CHECKS = {"mongo": mongo_ping, "model": model_loaded}
