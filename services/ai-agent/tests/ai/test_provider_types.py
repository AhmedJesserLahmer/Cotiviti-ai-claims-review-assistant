from ai_platform.providers.base import ChatMessage, LLMResponse, TokenUsage


def test_message_constructors():
    assert ChatMessage.system("s").role == "system"
    assert ChatMessage.user("u").role == "user"
    assert ChatMessage.assistant("a").content == "a"


def test_usage_totals_and_defaults():
    assert TokenUsage(10, 5).total_tokens == 15
    assert LLMResponse(text="x", provider="p", model="m").usage.total_tokens == 0
