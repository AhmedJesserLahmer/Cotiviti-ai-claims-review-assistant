import pytest

from ai_platform.prompts import CLAIM_RECOMMENDATION, CLAIM_REASONING, get_prompt


def test_reasoning_prompt_fences_untrusted_data():
    messages = CLAIM_REASONING.render(claim_json="{}", provider_json="{}", signals_json="{}")
    assert [m.role for m in messages] == ["system", "user"]
    assert "untrusted data" in messages[0].content
    assert "<claim_data>" in messages[1].content and "</claim_data>" in messages[1].content


def test_recommendation_prompt_lists_allowed_values():
    messages = CLAIM_RECOMMENDATION.render(reasoning="r", signals_json="{}", loop_note="")
    for value in ["approve", "flag_for_review", "request_more_data"]:
        assert value in messages[1].content


def test_registry_lookup_and_ids():
    assert get_prompt("claim_reasoning").id == "claim_reasoning@2.0.0"
    with pytest.raises(KeyError):
        get_prompt("nope")
