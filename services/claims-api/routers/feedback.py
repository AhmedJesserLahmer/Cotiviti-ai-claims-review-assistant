"""Reviewer feedback on AI decisions and AI quality analytics.

Feedback is the ground truth the AI layer is judged against: every record stores the
reviewer's final decision next to a snapshot of what the AI proposed (decision source,
model, prompt versions, overrides), so agreement can be sliced by any of them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.mongo import db

router = APIRouter(tags=["feedback"])

FinalDecision = Literal["approve", "deny", "flag_for_review", "request_more_data"]


class FeedbackIn(BaseModel):
    verdict: Literal["agree", "override"]
    final_decision: FinalDecision
    reviewer: str = Field(min_length=1, max_length=80)
    comment: str = Field(default="", max_length=1000)


class FeedbackOut(FeedbackIn):
    claim_id: str
    ai_recommendation: str
    ai_run_id: str | None = None
    ai_decision_source: str | None = None
    created_at: str


@router.post("/claims/{claim_id}/feedback", response_model=FeedbackOut, status_code=201)
async def submit_feedback(claim_id: str, body: FeedbackIn):
    analysis = await db["claim_analyses"].find_one({"claim_id": claim_id}, {"_id": 0})
    if not analysis:
        raise HTTPException(status_code=404, detail="No AI analysis to give feedback on for this claim")
    if body.verdict == "agree" and body.final_decision != analysis["recommendation"]:
        raise HTTPException(
            status_code=422,
            detail=f"'agree' requires final_decision == AI recommendation ({analysis['recommendation']})",
        )
    meta = analysis.get("ai_metadata") or {}
    record = {
        **body.model_dump(),
        "claim_id": claim_id,
        "ai_recommendation": analysis["recommendation"],
        "ai_run_id": meta.get("run_id"),
        "ai_decision_source": meta.get("decision_source"),
        "ai_model": meta.get("model_used"),
        "ai_prompt_versions": meta.get("prompt_versions"),
        "ai_policy_override": meta.get("recommendation_overridden", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db["claim_feedback"].insert_one(dict(record))
    return record


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


@router.get("/analytics/ai-quality")
async def ai_quality(limit: int = 5000):
    analyses = await db["claim_analyses"].find(
        {}, {"_id": 0, "recommendation": 1, "ai_metadata": 1}
    ).to_list(length=limit)
    feedback = await db["claim_feedback"].find({}, {"_id": 0}).to_list(length=limit)

    metas = [a.get("ai_metadata") or {} for a in analyses]
    by_source: dict[str, dict[str, int]] = {}
    for item in feedback:
        bucket = by_source.setdefault(item.get("ai_decision_source") or "unknown", {"total": 0, "agree": 0})
        bucket["total"] += 1
        bucket["agree"] += item["verdict"] == "agree"
    unsafe = sum(1 for f in feedback if f["ai_recommendation"] == "approve" and f["final_decision"] != "approve")

    return {
        "analyses": {
            "total": len(analyses),
            "by_recommendation": {
                rec: sum(1 for a in analyses if a.get("recommendation") == rec)
                for rec in ("approve", "flag_for_review", "request_more_data")
            },
            "rule_engine_rate": _rate(sum(1 for m in metas if m.get("decision_source") == "rules"), len(metas)),
            "model_fallback_rate": _rate(sum(1 for m in metas if m.get("model_fallback_used")), len(metas)),
            "policy_override_rate": _rate(sum(1 for m in metas if m.get("recommendation_overridden")), len(metas)),
            "injection_rate": _rate(sum(1 for m in metas if m.get("injection_detected")), len(metas)),
        },
        "feedback": {
            "total": len(feedback),
            "agreement_rate": _rate(sum(1 for f in feedback if f["verdict"] == "agree"), len(feedback)),
            # AI approved but the human did not: the costly error class.
            "unsafe_approval_rate": _rate(unsafe, sum(1 for f in feedback if f["ai_recommendation"] == "approve")),
            "agreement_by_source": {k: _rate(v["agree"], v["total"]) for k, v in by_source.items()},
        },
    }
