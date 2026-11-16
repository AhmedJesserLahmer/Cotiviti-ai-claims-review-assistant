"""Analysis calls delegated to the ai-agent service, with HTTP error mapping."""

from fastapi import HTTPException

from claims_common.contracts import AnalysisResult
from claims_common.http import ServiceResponseError, ServiceUnavailableError
from core.clients import get_ai_agent


async def request_analysis(claim_id: str) -> AnalysisResult:
    try:
        body = await get_ai_agent().post("/v1/analyses", json={"claim_id": claim_id})
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail="AI agent is unavailable, please retry shortly") from exc
    except ServiceResponseError as exc:
        status = exc.status_code if exc.status_code in (404, 422) else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    return AnalysisResult.model_validate(body)
