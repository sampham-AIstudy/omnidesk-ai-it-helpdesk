"""LLM service — Dynamic Multi-Provider Fallback Factory (Mistral -> OpenAI -> Local Ollama)."""
from __future__ import annotations

import os
import logging
from functools import lru_cache

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None


def get_provider_llm(model_type: str = "rag", temperature: float = 0.0, max_tokens: int = 1024):
    """
    Multi-Provider LLM Fallback Factory:
    1. Priority 1: Mistral API (nếu có MISTRAL_API_KEY trong .env)
    2. Priority 2: OpenAI API (nếu có OPENAI_API_KEY trong .env)
    3. Priority 3: Local Ollama (tự động chạy trên http://localhost:11434 khi không có API Key)
    """
    mistral_key = settings.mistral_api_key or os.getenv("MISTRAL_API_KEY", "")
    openai_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")

    # 1. Priority 1: Mistral AI
    if mistral_key and mistral_key.strip():
        try:
            from langchain_mistralai import ChatMistralAI
            model_attr = f"mistral_{model_type}_model"
            model_name = getattr(settings, model_attr, settings.mistral_rag_model)
            logger.info(f"Using Provider: Mistral AI ({model_name})")
            llm = ChatMistralAI(
                api_key=mistral_key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return _attach_fallback(llm)
        except Exception as e:
            logger.warning(f"Failed to initialize ChatMistralAI ({e}). Falling back to next provider...")

    # 2. Priority 2: OpenAI API
    if openai_key and openai_key.strip():
        try:
            from langchain_openai import ChatOpenAI
            model_name = settings.openai_model or "gpt-4o-mini"
            logger.info(f"Using Provider: OpenAI ({model_name})")
            return ChatOpenAI(
                api_key=openai_key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatOpenAI ({e}). Falling back to Local Ollama...")

    # 3. Priority 3: Local Ollama (Fallback khi không cài API Key)
    base_url = settings.ollama_base_url or "http://localhost:11434"
    model_name = settings.ollama_model or "mistral"
    logger.info(f"Using Provider: Local Ollama ({model_name} @ {base_url})")

    try:
        from langchain_community.llms.ollama import Ollama
        return Ollama(
            base_url=base_url,
            model=model_name,
            temperature=temperature,
        )
    except Exception as e:
        logger.error(f"Failed to initialize Local Ollama ({e}). Returning fallback client.")
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(api_key="dummy-key-for-offline", model="mistral-small-latest")


def _attach_fallback(primary_llm):
    """Gắn Fallback provider (Groq Llama-3.1) nếu có Groq Key và API chính bị Rate Limit."""
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and ChatGroq:
        try:
            fallback = ChatGroq(
                api_key=groq_key,
                model_name="llama-3.1-8b-instant",
                temperature=0.0,
                max_tokens=1024,
            )
            return primary_llm.with_fallbacks([fallback])
        except Exception:
            return primary_llm
    return primary_llm


@lru_cache
def get_classifier_llm():
    return get_provider_llm(model_type="classifier", temperature=0.0, max_tokens=1024)


@lru_cache
def get_fast_classifier_llm():
    return get_provider_llm(model_type="fast_classifier", temperature=0.0, max_tokens=512)


@lru_cache
def get_rag_llm():
    return get_provider_llm(model_type="rag", temperature=0.0, max_tokens=2048)


@lru_cache
def get_runbook_llm():
    return get_provider_llm(model_type="runbook", temperature=0.0, max_tokens=2048)


def get_model_by_complexity(complexity: str = "normal"):
    """
    Model Router — Định tuyến Mô hình theo Độ phức tạp tác vụ:
    - 'fast': Tốc độ siêu tốc cho Query Rewriting, Intent Classification.
    - 'normal': Phân tích RAG tiêu chuẩn.
    - 'complex': Mô hình suy luận sâu cho sự cố phức tạp & Runbook.
    """
    if complexity == "fast":
        return get_fast_classifier_llm()
    elif complexity == "complex":
        return get_runbook_llm()
    return get_rag_llm()
