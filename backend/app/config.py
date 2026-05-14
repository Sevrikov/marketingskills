from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    app_name: str = "ai-marketing-content-factory"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,null"

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/ai_content_factory"
    redis_url: str = "redis://localhost:6379/0"
    queue_mode: str = "rq"
    skill_registry_root: str = "../.agents/skills"
    operator_console_url: str = "http://127.0.0.1:5173"
    llm_provider: str = "mock"
    research_provider: str = "mock"
    source_provider: str = "mock"
    notification_provider: str = "mock"
    cms_provider: str = "mock"
    cms_destination_type: str = "generic_cms"
    image_generation_provider: str = "mock"

    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "ai-content-factory"

    google_api_key: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    gemini_content_model: str = "gemini-2.5-flash-lite"
    gemini_critic_model: str = "gemini-2.5-flash-lite"
    gemini_research_model: str = "gemini-2.5-flash-lite"
    gemini_image_model: str = "gemini-3.1-flash-image-preview"
    gemini_image_models: str = (
        "gemini-3.1-flash-image-preview,gemini-2.5-flash-image,gemini-3-pro-image-preview"
    )
    gemini_smoke_models: str = (
        "gemini-2.5-flash-lite,gemini-3-flash-preview,gemini-3.1-flash-lite-preview"
    )
    enable_gemini_quota_governor: bool = True
    gemini_quota_ledger_path: str = ".tmp/gemini_quota_ledger.json"
    gemini_daily_model_limits: str = (
        "gemini-2.5-flash-lite=20,"
        "gemini-3-flash-preview=20,"
        "gemini-3.1-flash-lite-preview=500,"
        "gemini-embedding-001=1000,"
        "gemini-embedding-2=1000"
    )
    gemini_unavailable_cooldown_seconds: int = 600

    tavily_api_key: str | None = None
    source_collection_enabled: bool = True
    source_collection_required: bool = False
    source_collection_max_results: int = 5
    source_corpus_max_chars: int = 20000
    tavily_search_depth: str = "basic"
    tavily_include_raw_content: str = "markdown"
    tavily_include_answer: str = "basic"
    tavily_country: str | None = None

    price_monitor_provider: str = "mock"
    price_monitor_timeout_seconds: int = 20
    price_monitor_user_agent: str = "AIContentFactoryPriceMonitor/0.1"

    viber_auth_token: str | None = None
    viber_reviewer_ids: str = ""
    viber_sender_name: str = "AI Content Factory"
    viber_webhook_public_url: str | None = None
    viber_webhook_event_types: str = "message,conversation_started,subscribed,unsubscribed,failed"
    viber_webhook_secret_required: bool = False

    telegram_bot_token: str | None = None
    telegram_approval_chat_id: str | None = None

    enable_real_publishing: bool = False
    enable_real_video_generation: bool = False
    enable_real_image_generation: bool = False
    enable_google_smoke_tests: bool = False
    monthly_ai_budget_usd: int = 100

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
