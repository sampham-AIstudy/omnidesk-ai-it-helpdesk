"""LLM service — Mistral client factory với phân bổ tối ưu theo Rate Limits (TPM/RPS)."""
from __future__ import annotations

from functools import lru_cache

from langchain_mistralai import ChatMistralAI

from src.config import get_settings

settings = get_settings()


import os
from functools import lru_cache
from langchain_mistralai import ChatMistralAI

from src.config import get_settings

settings = get_settings()

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None


def _attach_fallback(primary_llm):
    """Gắn Fallback provider (Groq Llama-3.1) nếu Mistral bị Rate Limit (HTTP 429)."""
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
    """High throughput model cho Classification (mistral-small-2506: 2.25M TPM, 5.0 RPS)."""
    primary = ChatMistralAI(
        api_key=settings.mistral_api_key,
        model=settings.mistral_classifier_model,
        temperature=0.0,
        max_tokens=1024,
    )
    return _attach_fallback(primary)


@lru_cache
def get_fast_classifier_llm():
    """Ultra-fast model cho Sub-second classification (ministral-3b-2512: 1.3M TPM, 12.5 RPS)."""
    primary = ChatMistralAI(
        api_key=settings.mistral_api_key,
        model=settings.mistral_fast_classifier_model,
        temperature=0.0,
        max_tokens=512,
    )
    return _attach_fallback(primary)


@lru_cache
def get_rag_llm():
    """High throughput RAG synthesis model (mistral-small-2506: 2.25M TPM, 5.0 RPS)."""
    primary = ChatMistralAI(
        api_key=settings.mistral_api_key,
        model=settings.mistral_rag_model,
        temperature=0.0,
        max_tokens=2048,
    )
    return _attach_fallback(primary)


@lru_cache
def get_runbook_llm():
    """Code & Command Generation model cho Runbook Execution (codestral-2508: 625K TPM, 2.08 RPS)."""
    primary = ChatMistralAI(
        api_key=settings.mistral_api_key,
        model=settings.mistral_runbook_model,
        temperature=0.0,
        max_tokens=2048,
    )
    return _attach_fallback(primary)


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

