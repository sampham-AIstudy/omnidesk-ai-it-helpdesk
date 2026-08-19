from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
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
    enable_demo_seed: bool | None = None
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Initial Production Administrator Provisioning
    initial_admin_email: str = ""
    initial_admin_username: str = "admin"
    initial_admin_password: str = ""
    initial_admin_full_name: str = "System Administrator"

    @field_validator("enable_demo_seed", mode="before")
    @classmethod
    def _parse_enable_demo_seed(cls, v: Any) -> bool | None:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            if v.lower() in ("true", "1", "yes"):
                return True
            if v.lower() in ("false", "0", "no"):
                return False
        return bool(v)

    # OpenTelemetry. The collector endpoint is internal to Docker Compose by
    # default; use localhost:4317 when running the backend on the host.
    otel_enabled: bool = False
    otel_service_name: str = "helpdesk-ai-agent"
    otel_service_version: str = "1.0.0"
    otel_service_namespace: str = ""
    otel_service_instance_id: str = ""
    otel_exporter_otlp_endpoint: str = "localhost:4317"
    otel_metric_export_interval_ms: int = Field(default=15000, ge=5000, le=60000)
    otel_traces_sampler: Literal["always_on", "always_off", "parentbased_traceidratio"] = "parentbased_traceidratio"
    otel_traces_sampler_arg: float = Field(default=1.0, ge=0.0, le=1.0)

    # LLM — Multi-Provider Config (Mistral / OpenAI / Local Ollama)
    mistral_api_key: str = ""
    mistral_classifier_model: str = "mistral-small-2506"
    mistral_rag_model: str = "mistral-small-2506"
    mistral_runbook_model: str = "codestral-2508"
    mistral_fast_classifier_model: str = "ministral-3b-2512"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Kept separate from the primary Mistral key so the fallback chain can be
    # configured from the same Settings source as every other provider.
    groq_api_key: str = ""

    # Dedicated key for the Gemini LLM fallback. It is intentionally separate
    # from google_api_key, which is reserved for security guardrails.
    gemini_api_key: str = ""

    # External evaluation judge. This is deliberately separate from the answer
    # model and is never used by the production Help Desk request path.
    eval_judge_base_url: str = "https://api.openai.com/v1"
    eval_judge_api_key: str = ""
    eval_judge_model: str = ""
    eval_judge_timeout_seconds: float = Field(default=90.0, ge=10.0, le=180.0)

    # NVIDIA NIM is used as the automatic external judge when the explicit
    # EVAL_JUDGE_* variables are not set.  It is deliberately not part of the
    # production LLM provider chain: production tickets and KB evidence must
    # not leave the approved providers by accident.
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    # 8B is the responsive hosted default for an automated quality gate. A
    # larger model may be selected explicitly for offline benchmark runs.
    nvidia_eval_judge_model: str = "meta/llama-3.1-8b-instruct"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/helpdesk.db"

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "helpdesk_kb_multilingual_v2_sentence_transformer"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_backend: Literal["sentence_transformer", "hashing"] = "sentence_transformer"
    embedding_allow_network_downloads: bool = False

    # Cross-Encoder Reranker (Optional second-stage reranker on top of hybrid retrieval)
    reranker_enabled: bool = False
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_n: int = Field(default=10, ge=2, le=50)

    # External research (only used after the internal RAG decision gate)
    web_research_enabled: bool = True
    web_search_provider: Literal["duckduckgo_html", "disabled"] = "duckduckgo_html"
    web_research_timeout_seconds: float = Field(default=6.0, ge=1.0, le=20.0)
    web_research_max_results: int = Field(default=4, ge=1, le=8)
    web_research_min_rag_score: float = Field(default=0.55, ge=0.0, le=1.0)
    rag_min_relevance_score: float = Field(default=0.55, ge=0.0, le=1.0)

    # Semantic duplicate ticket detection
    duplicate_high_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    duplicate_possible_threshold: float = Field(default=0.62, ge=0.0, le=1.0)
    duplicate_search_candidates: int = Field(default=24, ge=5, le=100)
    duplicate_spam_window_minutes: int = Field(default=30, ge=5, le=240)

    # Zero-Mem episodic retrieval.  These operations only use deterministic
    # parsing, SQLite/Chroma and embeddings; they never invoke an LLM.
    zero_mem_enabled: bool = True
    zero_mem_primary_view_weight: float = Field(default=0.60, ge=0.0, le=1.0)
    zero_mem_primary_candidates: int = Field(default=8, ge=1, le=30)
    zero_mem_final_evidence: int = Field(default=5, ge=1, le=12)
    zero_mem_neighbor_window: int = Field(default=1, ge=0, le=3)

    # Bounded short-term transcript context. This is intentionally distinct
    # from Zero-Mem relevance retrieval and never loads an entire thread.
    chat_recent_history_messages: int = Field(default=8, ge=0, le=32)
    ticket_recent_history_messages: int = Field(default=5, ge=0, le=32)
    chat_recent_history_message_chars: int = Field(default=1200, ge=100, le=4000)
    ticket_recent_history_message_chars: int = Field(default=1200, ge=100, le=4000)
    max_retrieval_query_chars: int = Field(default=400, ge=100, le=2000)

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
    # Gemini Safety Judge / guardrail key only; never use for LLM fallback.
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

    @property
    def is_demo_seed_enabled(self) -> bool:
        if self.enable_demo_seed is not None:
            return self.enable_demo_seed
        return self.app_env != "production"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env == "production":
            insecure_jwt_secrets = {
                "change-me-in-production",
                "helpdesk-super-secret-jwt-key-change-in-production-2024",
                "secret",
                "changeme",
                "admin",
                "password",
                "123456",
                "12345678",
                "default",
                "test",
            }
            secret = (self.jwt_secret or "").strip()
            if not secret:
                raise ValueError("In production mode, JWT_SECRET must not be empty.")
            if secret in insecure_jwt_secrets or len(secret) < 32:
                raise ValueError(
                    "In production mode, JWT_SECRET must be set to a secure, high-entropy key "
                    "(at least 32 characters) and cannot use development placeholders."
                )
            if self.cors_origins.strip() == "*":
                raise ValueError(
                    "In production mode, CORS_ORIGINS must not be wildcard '*' when credentials are enabled."
                )
        return self



@lru_cache
def get_settings() -> Settings:
    return Settings()
