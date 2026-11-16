"""Analysis calls delegated to the ai-agent service, with HTTP error mapping."""

import json

from fastapi import HTTPException

from claims_common.contracts import AnalysisResult
from claims_common.http import ServiceResponseError, ServiceUnavailableError
from core.clients import get_ai_agent


async def request_analysis(claim_id: str, *, refresh: bool = False) -> AnalysisResult:
    try:
        body = await get_ai_agent().post("/v1/analyses", json={"claim_id": claim_id, "bypass_cache": refresh})
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail="AI agent is unavailable, please retry shortly") from exc
    except ServiceResponseError as exc:
        status = exc.status_code if exc.status_code in (404, 422) else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    return AnalysisResult.model_validate(body)


async def proxy_analysis_stream(claim_id: str, *, refresh: bool = False):
    """Forward ai-agent's SSE stream; failures become a final SSE error event."""
    try:
        async for chunk in get_ai_agent().stream_bytes(
            "GET", f"/v1/analyses/{claim_id}/stream", params={"refresh": str(refresh).lower()}
        ):
            yield chunk
    except ServiceUnavailableError:
        yield _sse_error("AI agent is unavailable, please retry shortly", 503)
    except ServiceResponseError as exc:
        yield _sse_error(str(exc.detail), exc.status_code)


def _sse_error(detail: str, status: int) -> bytes:
    return f"event: error\ndata: {json.dumps({'detail': detail, 'status': status})}\n\n".encode()
