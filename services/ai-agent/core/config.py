from claims_common.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "ai-agent"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "claims_poc"
    # LLM settings (GROQ_API_KEY, GROQ_MODEL, AI_*) live in ai_platform.config.AISettings.


settings = Settings()
