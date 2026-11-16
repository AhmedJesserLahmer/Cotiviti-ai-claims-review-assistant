import pytest
from pydantic import ValidationError

from ai_platform.validation.schemas import RecommendationOutput


def test_valid_output():
    out = RecommendationOutput.model_validate(
        {"recommendation": "approve", "summary": " Looks fine. ", "confidence": 0.9, "key_factors": ["low risk"]}
    )
    assert out.summary == "Looks fine."


@pytest.mark.parametrize("raw, expected", [("Flag For Review", "flag_for_review"), ("approved", "approve"), ("more-data", "request_more_data")])
def test_recommendation_normalization(raw, expected):
    assert RecommendationOutput(recommendation=raw, summary="s").recommendation == expected


@pytest.mark.parametrize(
    "payload",
    [
        {"recommendation": "deny", "summary": "s"},
        {"recommendation": "approve", "summary": ""},
        {"recommendation": "approve", "summary": "s", "confidence": 1.5},
        {"recommendation": "approve"},
        {"recommendation": "approve", "summary": "x" * 401},
    ],
)
def test_invalid_outputs_rejected(payload):
    with pytest.raises(ValidationError):
        RecommendationOutput.model_validate(payload)


def test_key_factors_are_trimmed_and_capped():
    out = RecommendationOutput(recommendation="approve", summary="s", key_factors=[" a ", "", *"bcdefg"])
    assert out.key_factors == ["a", "b", "c", "d", "e"]
    assert RecommendationOutput(recommendation="approve", summary="s", key_factors="one").key_factors == ["one"]
