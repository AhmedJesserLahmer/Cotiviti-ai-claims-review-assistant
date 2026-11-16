from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "claims_poc"
    # LLM settings (GROQ_API_KEY, GROQ_MODEL, AI_*) live in ai_platform.config.AISettings.

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
