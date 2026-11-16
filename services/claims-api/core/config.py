from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "claims_poc"
    # Comma-separated list of browser origins allowed to call the API.
    cors_origins: str = "http://localhost:3000"
    # LLM settings (GROQ_API_KEY, GROQ_MODEL, AI_*) live in ai_platform.config.AISettings.

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS='*' is not allowed; list the dashboard origins explicitly")
        return origins


settings = Settings()
