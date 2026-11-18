"""Server-sent events for live analysis progress."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agent.graph import InvalidClaimDataError, MLUnavailableError, stream_analysis
from db.mongo import db

router = APIRouter(prefix="/v1", tags=["analyses"])
log = logging.getLogger("ai_agent.streams")

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.get("/analyses/{claim_id}/stream")
async def stream(claim_id: str, refresh: bool = False):
    claim = await db["claims"].find_one({"claim_id": claim_id}, {"_id": 0, "claim_id": 1})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    async def events():
        yield sse("start", {"claim_id": claim_id})
        try:
            async for event, payload in stream_analysis(claim_id, bypass_cache=refresh):
                yield sse(event, payload)
        except MLUnavailableError:
            yield sse("error", {"detail": "ML scoring is temporarily unavailable", "status": 503})
        except InvalidClaimDataError as exc:
            yield sse("error", {"detail": str(exc), "status": 422})
        except Exception as exc:  # noqa: BLE001 - the stream must end with an event, not a cut
            log.exception("analysis stream failed", extra={"claim_id": claim_id})
            yield sse("error", {"detail": f"analysis failed: {type(exc).__name__}", "status": 500})

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)
