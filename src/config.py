from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Help Desk AI Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # LLM — Mistral (primary)
    mistral_api_key: str = ""
    mistral_classifier_model: str = "mistral-small-2506"
    mistral_rag_model: str = "mistral-small-2506"
    mistral_runbook_model: str = "codestral-2508"
    mistral_fast_classifier_model: str = "ministral-3b-2512"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/helpdesk.db"

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "helpdesk_kb_multilingual_v1"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Auth / Security
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # SLA
    sla_warning_hours: int = 4
    sla_critical_hours: int = 8

    # Classifier Thresholds — chuẩn PRD FR-09: >=75%, 60–74%, <60%
    confidence_threshold_auto_close: float = Field(default=0.75, ge=0, le=1)
    confidence_threshold_warning: float = Field(default=0.60, ge=0, le=1)
    confidence_threshold_hitl: float = Field(default=0.60, ge=0, le=1)

    # LangSmith
    langchain_api_key: str = ""
    langchain_project: str = "helpdesk-ai-agent"
    langchain_tracing_v2: bool = True

    # Redis Cache (standard Redis preferred; Upstash REST fallback)
    redis_url: str = ""
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    redis_cache_ttl: int = 3600  # seconds — 1 hour default

    # AI Hook Logging
    ai_log_server: str = ""
    ai_log_api_key: str = ""
    ai_log_dir: str = ".ai-log"

    # Security & Guardrail Integrations
    google_api_key: str = ""
    google_genai_use_vertexai: int = 0
    rate_limit_max_requests: int = 10
    rate_limit_window_seconds: int = 60
    block_rate_threshold: float = 0.5
    judge_fail_rate_threshold: float = 0.3
    lakeraguard_api_key: str = ""
    virustotal_api_key: str = ""
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""
    google_safe_browsing_api: str = ""
    openai_moderation_api: str = ""



@lru_cache
def get_settings() -> Settings:
    return Settings()
