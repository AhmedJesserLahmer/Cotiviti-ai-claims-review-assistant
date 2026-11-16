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

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS='*' is not allowed; list the dashboard origins explicitly")
        return origins

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}
