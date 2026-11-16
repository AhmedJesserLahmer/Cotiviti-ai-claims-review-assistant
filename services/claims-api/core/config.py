from claims_common.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "claims-api"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "claims_poc"
    # Internal URL of the AI agent service.
    ai_agent_url: str = "http://localhost:8002"
    # An analysis runs ML + up to four LLM calls (with retries); allow for that.
    ai_agent_timeout_s: float = 90.0


settings = Settings()
