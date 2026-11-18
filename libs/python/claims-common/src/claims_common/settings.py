"""Base settings shared by every service."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "claims-service"
    environment: str = "local"  # local | dev | staging | prod
    log_level: str = "INFO"
    log_format: str = "json"
    # Comma-separated list of browser origins allowed to call the service.
    cors_origins: str = "http://localhost:3000"
    # HMAC key signing audit-log entries (>= 32 chars, required in production).
    audit_hmac_key: str = ""
    # /metrics for Prometheus. In Kubernetes a NetworkPolicy restricts who can scrape it.
    metrics_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS='*' is not allowed; list the dashboard origins explicitly")
        return origins

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}

    def audit_key(self) -> str:
        from claims_common.audit_log import DEV_KEY

        if self.audit_hmac_key:
            if self.is_production and len(self.audit_hmac_key) < 32:
                raise RuntimeError("AUDIT_HMAC_KEY must be at least 32 characters in production")
            return self.audit_hmac_key
        if self.is_production:
            raise RuntimeError("AUDIT_HMAC_KEY is required when ENVIRONMENT=prod")
        return DEV_KEY
