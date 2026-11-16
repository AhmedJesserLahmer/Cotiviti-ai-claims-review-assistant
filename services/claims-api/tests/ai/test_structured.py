import pytest

from ai_platform.client import ResilientLLMClient
from ai_platform.errors import OutputValidationError
from ai_platform.providers.base import ChatMessage
from ai_platform.providers.scripted import ScriptedProvider
from ai_platform.validation.schemas import RecommendationOutput
from ai_platform.validation.structured import generate_structured

MSG = [ChatMessage.user("decide")]
GOOD = '{"recommendation": "approve", "summary": "fine"}'


class Counter:
    def __init__(self):
        self.repairs = []

    def record_repair(self, error):
        self.repairs.append(error)


async def test_valid_first_reply_needs_no_repair():
    provider = ScriptedProvider([GOOD])
    out = await generate_structured(ResilientLLMClient([provider]), MSG, RecommendationOutput)
    assert out.recommendation == "approve"
    assert len(provider.calls) == 1


async def test_invalid_reply_is_repaired_with_error_feedback():
    provider = ScriptedProvider(['{"recommendation": "deny", "summary": "no"}', GOOD])
    counter = Counter()
    out = await generate_structured(
        ResilientLLMClient([provider]), MSG, RecommendationOutput, max_repairs=1, counter=counter, schema_hint="HINT"
    )
    assert out.recommendation == "approve"
    repair_turn = provider.calls[1]
    assert repair_turn[-2].role == "assistant"
    assert "recommendation" in repair_turn[-1].content and "HINT" in repair_turn[-1].content
    assert len(counter.repairs) == 1


async def test_gives_up_after_max_repairs():
    provider = ScriptedProvider(["not json", "still not json"])
    with pytest.raises(OutputValidationError):
        await generate_structured(ResilientLLMClient([provider]), MSG, RecommendationOutput, max_repairs=1)
    assert len(provider.calls) == 2


async def test_zero_repairs_fails_fast():
    provider = ScriptedProvider(["nope"])
    with pytest.raises(OutputValidationError):
        await generate_structured(ResilientLLMClient([provider]), MSG, RecommendationOutput, max_repairs=0)
