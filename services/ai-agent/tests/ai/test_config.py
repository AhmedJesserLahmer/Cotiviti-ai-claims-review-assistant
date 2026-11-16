from ai_platform.config import AISettings


def _clean_env(monkeypatch):
    for key in ["GROQ_API_KEY", "GROQ_MODEL", "AI_FALLBACK_MODELS", "AI_OFFLINE_MODE", "AI_MAX_RETRIES"]:
        monkeypatch.delenv(key, raising=False)


def test_defaults_without_key_disable_llm(monkeypatch):
    _clean_env(monkeypatch)
    settings = AISettings(_env_file=None)
    assert not settings.llm_enabled
    assert settings.model_chain[0] == "llama-3.3-70b-versatile"


def test_placeholder_key_is_not_a_credential(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "your_groq_api_key_here")
    assert not AISettings(_env_file=None).has_llm_credentials


def test_env_overrides_and_model_chain_dedup(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_real")
    monkeypatch.setenv("GROQ_MODEL", "model-a")
    monkeypatch.setenv("AI_FALLBACK_MODELS", "model-b, model-a ,model-c")
    monkeypatch.setenv("AI_MAX_RETRIES", "4")
    settings = AISettings(_env_file=None)
    assert settings.llm_enabled
    assert settings.model_chain == ["model-a", "model-b", "model-c"]
    assert settings.max_retries == 4


def test_offline_mode_disables_llm(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_real")
    monkeypatch.setenv("AI_OFFLINE_MODE", "true")
    assert not AISettings(_env_file=None).llm_enabled
