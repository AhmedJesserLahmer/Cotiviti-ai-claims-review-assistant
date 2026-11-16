import pytest

from ai_platform.calibration import calibrate, ml_support

PROBS = {"Low": 0.7, "Medium": 0.2, "High": 0.1}


def test_ml_support_by_decision():
    assert ml_support("approve", PROBS) == pytest.approx(0.8)
    assert ml_support("flag_for_review", PROBS) == pytest.approx(0.2)
    assert ml_support("request_more_data", PROBS) == 0.5


def test_blend_and_penalties():
    signals = {"risk_probabilities": PROBS}
    assert calibrate("approve", 0.9, signals, from_rules=False) == 0.85
    assert calibrate("approve", None, signals, from_rules=False) == 0.65
    assert calibrate("approve", 0.9, {**signals, "ood_flags": ["x"]}, from_rules=False) == 0.68
    assert calibrate("approve", 0.9, {**signals, "signals_source": "cache"}, from_rules=False) == 0.68
    assert calibrate("approve", 0.9, signals, from_rules=True) == 0.6


async def test_overconfident_llm_approval_against_ml_evidence_abstains():
    from ai_platform.audit import AIRunMetadata
    from ai_platform.client import ResilientLLMClient
    from ai_platform.config import AISettings
    from ai_platform.providers.scripted import ScriptedProvider
    from ai_platform.service import ClaimReviewAI
    from tests.ai.test_service import CLAIM, PROVIDER, SIGNALS

    # Classifier leans Medium/High but below the high-risk policy threshold.
    signals = {**SIGNALS, "predicted_risk_label": "Medium", "risk_probabilities": {"Low": 0.1, "Medium": 0.45, "High": 0.45}}
    approve = '{"recommendation": "approve", "summary": "fine", "confidence": 0.6}'
    ai = ClaimReviewAI(ResilientLLMClient([ScriptedProvider(["1. ok", approve])]), AISettings(_env_file=None, groq_api_key="x"))
    run = AIRunMetadata()
    reasoning = await ai.reason(claim=CLAIM, provider=PROVIDER, signals=signals, run=run)
    out = await ai.recommend(claim=CLAIM, signals=signals, reasoning=reasoning, allow_more_data=True, run=run)
    assert out.recommendation == "flag_for_review" and "low_confidence" in out.key_factors
