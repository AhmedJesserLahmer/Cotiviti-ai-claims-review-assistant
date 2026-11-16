"""Schemas that LLM output must satisfy before the system acts on it."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Recommendation = Literal["approve", "flag_for_review", "request_more_data"]
RECOMMENDATIONS: tuple[str, ...] = ("approve", "flag_for_review", "request_more_data")

_ALIASES = {
    "approved": "approve",
    "accept": "approve",
    "flag": "flag_for_review",
    "flagged": "flag_for_review",
    "review": "flag_for_review",
    "manual_review": "flag_for_review",
    "request_data": "request_more_data",
    "more_data": "request_more_data",
}


class RecommendationOutput(BaseModel):
    """Decision returned by the recommendation step (LLM or rule engine)."""

    model_config = ConfigDict(extra="ignore")

    recommendation: Recommendation
    summary: str = Field(min_length=1, max_length=400)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    key_factors: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("recommendation", mode="before")
    @classmethod
    def _normalize_recommendation(cls, value):
        # Accept harmless variations ("Flag For Review", "flag-for-review"); anything
        # outside the allowed set still fails validation.
        if isinstance(value, str):
            key = value.strip().lower().replace("-", "_").replace(" ", "_")
            return _ALIASES.get(key, key)
        return value

    @field_validator("summary", mode="before")
    @classmethod
    def _strip_summary(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("key_factors", mode="before")
    @classmethod
    def _clean_factors(cls, value):
        if isinstance(value, str):
            value = [value]
        if isinstance(value, list):
            return [str(v).strip()[:120] for v in value if str(v).strip()][:5]
        return value


def schema_hint() -> str:
    """Short human-readable description used in repair prompts."""
    return (
        '{"recommendation": "approve" | "flag_for_review" | "request_more_data", '
        '"summary": "<one sentence>", "confidence": <0..1>, "key_factors": ["..."]}'
    )
