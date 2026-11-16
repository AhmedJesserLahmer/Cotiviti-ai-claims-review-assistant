from ai_platform.audit import AIRunMetadata
from ai_platform.client import ResilientLLMClient
from ai_platform.config import AISettings
from ai_platform.errors import LLMAuthError
from ai_platform.providers.scripted import ScriptedProvider
from ai_platform.service import ClaimReviewAI
from tests.ai.test_service import APPROVE, CLAIM, PROVIDER, SIGNALS


async def run(script, **settings):
    provider = ScriptedProvider(script)
    ai = ClaimReviewAI(ResilientLLMClient([provider]), AISettings(_env_file=None, groq_api_key="x", judge_enabled=True, **settings))
    meta = AIRunMetadata()
    reasoning = await ai.reason(claim=CLAIM, provider=PROVIDER, signals=SIGNALS, run=meta)
    out = await ai.recommend(claim=CLAIM, signals=SIGNALS, reasoning=reasoning, allow_more_data=True, run=meta)
    return out, meta, provider


async def test_consistent_approval_passes_the_judge():
    out, meta, provider = await run(["1. ok", APPROVE, '{"consistent": true, "issues": []}'])
    assert out.recommendation == "approve" and meta.judge["consistent"] is True
    assert "claim_judge" in meta.prompt_versions and len(provider.calls) == 3


async def test_inconsistent_approval_is_escalated():
    out, meta, _ = await run(["1. ok", APPROVE, '{"consistent": false, "issues": ["cites $5,000 but billed is $1,000"]}'])
    assert out.recommendation == "flag_for_review" and meta.recommendation_overridden
    assert "judge_inconsistent" in out.key_factors


async def test_judge_failure_is_fail_open_by_default_and_fail_closed_on_request():
    out, meta, _ = await run(["1. ok", APPROVE, LLMAuthError("down")])
    assert out.recommendation == "approve" and meta.judge["consistent"] is None
    out, _, _ = await run(["1. ok", APPROVE, LLMAuthError("down")], judge_fail_closed=True)
    assert out.recommendation == "flag_for_review"


async def test_flags_are_not_judged():
    flag = '{"recommendation": "flag_for_review", "summary": "check it"}'
    out, meta, provider = await run(["1. ok", flag])
    assert meta.judge is None and len(provider.calls) == 2
