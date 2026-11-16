import pytest

from ai_platform.errors import OutputParseError
from ai_platform.validation.parsing import extract_json_object

EXPECTED = {"recommendation": "approve", "summary": "ok"}


@pytest.mark.parametrize(
    "text",
    [
        '{"recommendation": "approve", "summary": "ok"}',
        '```json\n{"recommendation": "approve", "summary": "ok"}\n```',
        '```\n{"recommendation": "approve", "summary": "ok"}```',
        'Here is my decision:\n{"recommendation": "approve", "summary": "ok"}\nThanks!',
        '{"recommendation": "approve", "summary": "ok",}',
        "{'recommendation': 'approve', 'summary': 'ok'}",
        "{“recommendation”: “approve”, “summary”: “ok”}",
    ],
)
def test_recovers_common_llm_formats(text):
    assert extract_json_object(text) == EXPECTED


def test_braces_inside_strings_do_not_confuse_extraction():
    text = 'Answer: {"recommendation": "approve", "summary": "uses {curly} braces"} done'
    assert extract_json_object(text)["summary"] == "uses {curly} braces"


def test_python_literals_are_converted():
    assert extract_json_object("{'ok': True, 'x': None}") == {"ok": True, "x": None}


def test_apostrophes_in_valid_json_are_preserved():
    assert extract_json_object('{"summary": "provider\'s history is clean"}')["summary"] == "provider's history is clean"


@pytest.mark.parametrize("text", ["", "   ", "I think we should approve it.", "[1, 2, 3]", "{broken"])
def test_unrecoverable_output_raises(text):
    with pytest.raises(OutputParseError):
        extract_json_object(text)
