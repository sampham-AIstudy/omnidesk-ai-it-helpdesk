"""LLM service — Dynamic Multi-Provider Fallback Factory (Mistral -> OpenAI -> Local Ollama)."""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import weakref
from typing import Any

from pydantic import SecretStr

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None  # type: ignore[misc,assignment]


def get_gemini_api_key() -> str:
    """Return only the dedicated Gemini fallback key, never the guardrail key."""
    return settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")


def get_groq_api_key() -> str:
    """Read Groq fallback credentials through Settings, including the project .env."""
    return getattr(settings, "groq_api_key", "") or os.getenv("GROQ_API_KEY", "")


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
            model_name = str(getattr(settings, model_attr, settings.mistral_rag_model) or "mistral-small-latest")
            logger.info(f"Using Provider: Mistral AI ({model_name})")
            llm = ChatMistralAI(
                api_key=SecretStr(mistral_key),
                model_name=model_name,
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
                api_key=SecretStr(openai_key),
                model=model_name,
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatOpenAI ({e}). Falling back to Local Ollama...")

    # 3. Priority 3: Local Ollama (Fallback khi không cài API Key)
    base_url = settings.ollama_base_url or "http://localhost:11434"
    model_name = settings.ollama_model or "mistral"
    logger.info(f"Using Provider: Local Ollama ({model_name} @ {base_url})")

    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=base_url,
            model=model_name,
            temperature=temperature,
        )
    except Exception as e:
        logger.error(f"Failed to initialize Local Ollama ({e}). Returning fallback client.")
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            api_key=SecretStr("dummy-key-for-offline"),
            model_name="mistral-small-latest",
        )


def _attach_fallback(primary_llm):
    """Gắn chuỗi Fallback providers (Groq -> Gemini 3.5 Flash-Lite -> Local Ollama) khi API chính bị Rate Limit / lỗi."""
    fallbacks: list[Any] = []

    # 1. Fallback 1: Groq (Llama 3.1 8B Instant)
    groq_key = get_groq_api_key()
    if groq_key and ChatGroq is not None:
        try:
            fallbacks.append(
                ChatGroq(
                    api_key=SecretStr(groq_key),
                    model="llama-3.1-8b-instant",
                    temperature=0.0,
                    max_tokens=1024,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatGroq fallback: {e}")

    # 2. Fallback 2: Google Gemini 3.5 Flash-Lite (langchain-google-genai HOẶC native google.genai SDK)
    # GOOGLE_API_KEY is reserved for the output safety judge. Ticket prompts
    # may reach this fallback only with the dedicated GEMINI_API_KEY.
    gemini_key = get_gemini_api_key()
    if gemini_key and gemini_key.strip():
        gemini_added = False
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            fallbacks.append(
                ChatGoogleGenerativeAI(
                    model="gemini-3.5-flash-lite",
                    google_api_key=SecretStr(gemini_key),
                    temperature=0.0,
                )
            )
            gemini_added = True
        except Exception:
            pass

        if not gemini_added:
            try:
                import google.genai as genai
                from langchain_core.messages import AIMessage
                from langchain_core.runnables import RunnableLambda

                def _gemini_genai_call(input_val):
                    client = genai.Client(api_key=gemini_key)
                    if hasattr(input_val, "to_string"):
                        prompt_str = input_val.to_string()
                    elif isinstance(input_val, list):
                        prompt_str = "\n".join(str(m.content if hasattr(m, 'content') else m) for m in input_val)
                    else:
                        prompt_str = str(input_val)

                    try:
                        res = client.models.generate_content(
                            model="gemini-3.5-flash-lite",
                            contents=prompt_str,
                        )
                    except Exception:
                        res = client.models.generate_content(
                            model="gemini-3.5-flash-lite",
                            contents=prompt_str,
                        )
                    return AIMessage(content=res.text or "")

                fallbacks.append(RunnableLambda(_gemini_genai_call))
                gemini_added = True
                logger.info("Successfully registered Gemini 3.5 Flash-Lite via native google.genai SDK fallback")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini 3.5 Flash-Lite fallback: {e}")

    # 3. Fallback 3: Local Ollama (Cuối cùng nếu mất mạng/hết quota cloud)
    try:
        from langchain_ollama import ChatOllama
        base_url = settings.ollama_base_url or "http://localhost:11434"
        model_name = settings.ollama_model or "mistral"
        fallbacks.append(
            ChatOllama(
                base_url=base_url,
                model=model_name,
                temperature=0.0,
            )
        )
    except Exception as e:
        logger.warning(f"Failed to initialize ChatOllama fallback: {e}")

    if fallbacks:
        logger.info(f"Attached {len(fallbacks)} fallback LLM provider(s) to primary LLM.")
        return primary_llm.with_fallbacks(fallbacks)
    return primary_llm


_cache_lock = threading.RLock()
_loop_llm_cache: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[tuple[str, float, int], Any]] = (
    weakref.WeakKeyDictionary()
)


def clear_llm_cache() -> None:
    """Explicitly clear all cached LLM instances."""
    with _cache_lock:
        _loop_llm_cache.clear()


def _get_or_create_loop_llm(model_type: str, temperature: float, max_tokens: int) -> Any:
    """Retrieve or create an LLM instance scoped to the currently running event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and not loop.is_closed():
        with _cache_lock:
            loop_entries = _loop_llm_cache.setdefault(loop, {})
            key = (model_type, temperature, max_tokens)
            if key in loop_entries:
                return loop_entries[key]
            instance = get_provider_llm(model_type=model_type, temperature=temperature, max_tokens=max_tokens)
            loop_entries[key] = instance
            return instance

    return get_provider_llm(model_type=model_type, temperature=temperature, max_tokens=max_tokens)


def get_classifier_llm():
    return _get_or_create_loop_llm(model_type="classifier", temperature=0.0, max_tokens=1024)


def get_fast_classifier_llm():
    return _get_or_create_loop_llm(model_type="fast_classifier", temperature=0.0, max_tokens=512)


def get_rag_llm():
    return _get_or_create_loop_llm(model_type="rag", temperature=0.0, max_tokens=2048)


def get_runbook_llm():
    return _get_or_create_loop_llm(model_type="runbook", temperature=0.0, max_tokens=2048)


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
