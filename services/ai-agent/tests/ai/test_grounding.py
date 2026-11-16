from ai_platform.audit import AIRunMetadata
from ai_platform.client import ResilientLLMClient
from ai_platform.config import AISettings
from ai_platform.guardrails.grounding import check_grounding
from ai_platform.providers.scripted import ScriptedProvider
from ai_platform.service import ClaimReviewAI
from tests.ai.test_service import APPROVE, CLAIM, PROVIDER, SIGNALS


def test_correct_numbers_are_grounded():
    text = "Billed $1,000.00 vs predicted $900; P(Low) is 80%, only 5% High; ratio 1.11x, about 11% above."
    report = check_grounding(text, CLAIM, SIGNALS)
    assert report.checked == 6 and report.ungrounded == []


def test_invented_numbers_are_reported():
    report = check_grounding("Billed $5,200 with 42% high risk, 3.5x the prediction.", CLAIM, SIGNALS)
    assert report.ungrounded == ["$5,200", "42%", "3.5x"]


def test_text_without_numbers_has_nothing_to_check():
    assert check_grounding("Looks routine.", CLAIM, SIGNALS).checked == 0


async def _run(reasoning):
    ai = ClaimReviewAI(ResilientLLMClient([ScriptedProvider([reasoning, APPROVE])]), AISettings(_env_file=None, groq_api_key="x"))
    run = AIRunMetadata()
    text = await ai.reason(claim=CLAIM, provider=PROVIDER, signals=SIGNALS, run=run)
    return await ai.recommend(claim=CLAIM, signals=SIGNALS, reasoning=text, allow_more_data=True, run=run), run


async def test_hallucinated_reasoning_blocks_approval():
    out, run = await _run("1. Billed $7,777 is fine.\n2. Risk 66% is acceptable.")
    assert out.recommendation == "flag_for_review" and "ungrounded_reasoning" in out.key_factors
    assert run.grounding["ungrounded"] == ["$7,777", "66%"]


async def test_one_rounding_slip_only_warns():
    out, run = await _run("1. Billed $1,000.\n2. Risk 66% overall.")
    assert out.recommendation == "approve"
    assert any(e.guardrail == "grounding" for e in run.guardrail_events)
