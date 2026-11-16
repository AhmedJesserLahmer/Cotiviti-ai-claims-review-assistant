import pytest

from ai_platform.audit import AIRunMetadata
from ai_platform.client import ResilientLLMClient
from ai_platform.config import AISettings
from ai_platform.pricing import estimate_cost, parse_prices
from ai_platform.providers.base import TokenUsage
from ai_platform.providers.scripted import ScriptedProvider
from ai_platform.service import ClaimReviewAI
from tests.ai.test_service import APPROVE, CLAIM, PROVIDER, SIGNALS


def test_price_parsing_and_estimates():
    prices = parse_prices("a=1/2; b=0.5/0.5")
    assert prices == {"a": (1.0, 2.0), "b": (0.5, 0.5)}
    assert estimate_cost("a", 1_000_000, 500_000, prices) == pytest.approx(2.0)
    assert estimate_cost("unknown", 10, 10, prices) == 0.0
    with pytest.raises(ValueError):
        parse_prices("broken")


async def test_usage_and_cost_are_accumulated_per_run():
    provider = ScriptedProvider(["1. ok", APPROVE], model="m", usage=TokenUsage(1000, 200))
    settings = AISettings(_env_file=None, groq_api_key="x", model_prices="m=1/2")
    ai = ClaimReviewAI(ResilientLLMClient([provider]), settings)
    run = AIRunMetadata()
    reasoning = await ai.reason(claim=CLAIM, provider=PROVIDER, signals=SIGNALS, run=run)
    await ai.recommend(claim=CLAIM, signals=SIGNALS, reasoning=reasoning, allow_more_data=True, run=run)
    assert run.prompt_tokens == 2000 and run.completion_tokens == 400
    assert run.estimated_cost_usd == pytest.approx((2000 * 1 + 400 * 2) / 1e6)


async def test_exhausted_budget_degrades_to_rules():
    provider = ScriptedProvider(["1. ok", APPROVE], usage=TokenUsage(900, 100))
    settings = AISettings(_env_file=None, groq_api_key="x", max_tokens_per_run=1000)
    ai = ClaimReviewAI(ResilientLLMClient([provider]), settings)
    run = AIRunMetadata()
    reasoning = await ai.reason(claim=CLAIM, provider=PROVIDER, signals=SIGNALS, run=run)
    await ai.recommend(claim=CLAIM, signals=SIGNALS, reasoning=reasoning, allow_more_data=True, run=run)
    assert run.decision_source == "rules" and "budget" in run.degraded_reason
    assert len(provider.calls) == 1
