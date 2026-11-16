from claims_common.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "claims-api"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "claims_poc"
    # Internal URL of the AI agent service.
    ai_agent_url: str = "http://localhost:8002"
    # Internal URL of the ML service (owns the synthetic dataset and seeding).
    ml_service_url: str = "http://localhost:8001"
    # An analysis runs ML + up to four LLM calls (with retries); allow for that.
    ai_agent_timeout_s: float = 90.0
    # Parallel analyses per job (bounded so a big upload cannot flood ai-agent / the LLM).
    analysis_concurrency: int = 4
    max_job_claims: int = 500
    # Per-client limits on endpoints that trigger LLM work.
    rate_limit_enabled: bool = True
    rate_limit_analyze_per_minute: int = 30
    rate_limit_bulk_per_minute: int = 6
    # When set, jobs are queued in Redis and executed by the arq worker deployment.
    redis_url: str | None = None


settings = Settings()
