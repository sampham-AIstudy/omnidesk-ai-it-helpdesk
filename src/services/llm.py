"""LLM service — Mistral client factory với phân bổ tối ưu theo Rate Limits (TPM/RPS)."""
from __future__ import annotations

from functools import lru_cache
from langchain_mistralai import ChatMistralAI

from src.config import get_settings

settings = get_settings()


@lru_cache
def get_classifier_llm() -> ChatMistralAI:
    """High throughput model cho Classification (mistral-small-2506: 2.25M TPM, 5.0 RPS)."""
    return ChatMistralAI(
        api_key=settings.mistral_api_key,
        model=settings.mistral_classifier_model,
        temperature=0.0,
        max_tokens=1024,
    )


@lru_cache
def get_fast_classifier_llm() -> ChatMistralAI:
    """Ultra-fast model cho Sub-second classification (ministral-3b-2512: 1.3M TPM, 12.5 RPS)."""
    return ChatMistralAI(
        api_key=settings.mistral_api_key,
        model=settings.mistral_fast_classifier_model,
        temperature=0.0,
        max_tokens=512,
    )


@lru_cache
def get_rag_llm() -> ChatMistralAI:
    """High throughput RAG synthesis model (mistral-small-2506: 2.25M TPM, 5.0 RPS)."""
    return ChatMistralAI(
        api_key=settings.mistral_api_key,
        model=settings.mistral_rag_model,
        temperature=0.2,
        max_tokens=2048,
    )


@lru_cache
def get_runbook_llm() -> ChatMistralAI:
    """Code & Command Generation model cho Runbook Execution (codestral-2508: 625K TPM, 2.08 RPS)."""
    return ChatMistralAI(
        api_key=settings.mistral_api_key,
        model=settings.mistral_runbook_model,
        temperature=0.0,
        max_tokens=2048,
    )
