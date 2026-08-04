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


    # LLM — OpenAI (optional fallback)
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/helpdesk.db"

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "helpdesk_kb"

    # Auth / Security
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # SLA
    sla_warning_hours: int = 4
    sla_critical_hours: int = 8

    # Classifier Thresholds
    confidence_threshold_auto_close: float = 0.85
    confidence_threshold_hitl: float = 0.70


    # LangSmith
    langchain_api_key: str = ""
    langchain_project: str = "helpdesk-ai-agent"
    langchain_tracing_v2: bool = True

    # AI Hook Logging
    ai_log_server: str = ""
    ai_log_api_key: str = ""
    ai_log_dir: str = ".ai-log"


@lru_cache
def get_settings() -> Settings:
    return Settings()
