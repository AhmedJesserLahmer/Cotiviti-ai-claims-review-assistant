import pytest

from ai_platform.audit import AIRunMetadata
from ai_platform.client import ResilientLLMClient
from ai_platform.config import AISettings
from ai_platform.prompts import get_prompt, parse_traffic, select_prompt
from ai_platform.providers.scripted import ScriptedProvider
from ai_platform.service import ClaimReviewAI
from tests.ai.test_service import APPROVE, CLAIM, PROVIDER, SIGNALS


def test_traffic_parsing_and_validation():
    assert parse_traffic("claim_reasoning@2.1.0=0.25") == {"claim_reasoning": {"2.1.0": 0.25}}
    assert parse_traffic("") == {}
    for bad in ["claim_reasoning@9.9.9=0.1", "claim_reasoning@2.1.0=1.5", "nope", "claim_reasoning@2.1.0=0.6,claim_reasoning@2.0.0=0.6"]:
        with pytest.raises((ValueError, KeyError)):
            parse_traffic(bad)


def test_assignment_is_deterministic_and_respects_share():
    traffic = parse_traffic("claim_reasoning@2.1.0=0.3")
    picks = [select_prompt("claim_reasoning", f"CLM{i}", traffic).version for i in range(2000)]
    assert picks == [select_prompt("claim_reasoning", f"CLM{i}", traffic).version for i in range(2000)]
    assert 0.25 < picks.count("2.1.0") / len(picks) < 0.35
    assert select_prompt("claim_recommendation", "x", traffic).version == get_prompt("claim_recommendation").version


async def test_variant_version_is_recorded_in_the_run():
    settings = AISettings(_env_file=None, groq_api_key="x", prompt_traffic="claim_reasoning@2.1.0=1.0")
    provider = ScriptedProvider(["1. ok", APPROVE])
    ai = ClaimReviewAI(ResilientLLMClient([provider]), settings)
    run = AIRunMetadata()
    await ai.reason(claim=CLAIM, provider=PROVIDER, signals=SIGNALS, run=run)
    assert run.prompt_versions["claim_reasoning"] == "2.1.0"
    assert "single signal" in provider.calls[0][1].content
