"""Environment-driven configuration for the AI layer.

All knobs use the ``AI_`` prefix (e.g. ``AI_REQUEST_TIMEOUT_S=15``). The Groq key and
primary model keep their existing names (``GROQ_API_KEY``, ``GROQ_MODEL``) so current
deployments keep working.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_KEYS = {"", "your_groq_api_key_here"}


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AI_", env_file=".env", extra="ignore", populate_by_name=True
    )

    # --- providers -------------------------------------------------------------
    groq_api_key: str = Field(default="", validation_alias=AliasChoices("GROQ_API_KEY", "AI_GROQ_API_KEY"))
    primary_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias=AliasChoices("GROQ_MODEL", "AI_PRIMARY_MODEL"),
    )
    # Comma-separated list, tried in order after the primary model fails.
    fallback_models: str = "llama-3.1-8b-instant"
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    # Forces the deterministic rule engine (demos, CI, or an LLM outage drill).
    offline_mode: bool = False

    # --- resilience ------------------------------------------------------------
    request_timeout_s: float = Field(default=20.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    backoff_base_s: float = Field(default=0.5, ge=0)
    backoff_max_s: float = Field(default=8.0, ge=0)
    circuit_failure_threshold: int = Field(default=5, ge=1)
    circuit_recovery_s: float = Field(default=30.0, gt=0)

    # --- caching ---------------------------------------------------------------
    cache_enabled: bool = True
    cache_ttl_s: int = Field(default=3600, ge=1)
    cache_max_entries: int = Field(default=1000, ge=1)
    # Shared cache for all replicas; in-process LRU when unset.
    cache_redis_url: str | None = None

    # --- validation ------------------------------------------------------------
    max_repair_attempts: int = Field(default=1, ge=0, le=5)

    # --- guardrails ------------------------------------------------------------
    guardrails_enabled: bool = True
    pii_redaction_enabled: bool = True
    policy_enforcement_enabled: bool = True
    max_field_chars: int = Field(default=200, ge=16)
    max_reasoning_chars: int = Field(default=2500, ge=200)
    high_risk_probability_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    billing_ratio_threshold: float = Field(default=2.5, gt=1.0)

    @property
    def fallback_model_list(self) -> list[str]:
        return [m.strip() for m in self.fallback_models.split(",") if m.strip()]

    @property
    def model_chain(self) -> list[str]:
        """Primary model first, then fallbacks, without duplicates."""
        chain: list[str] = []
        for model in [self.primary_model, *self.fallback_model_list]:
            if model not in chain:
                chain.append(model)
        return chain

    @property
    def has_llm_credentials(self) -> bool:
        return self.groq_api_key.strip() not in _PLACEHOLDER_KEYS

    @property
    def llm_enabled(self) -> bool:
        return self.has_llm_credentials and not self.offline_mode


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()
