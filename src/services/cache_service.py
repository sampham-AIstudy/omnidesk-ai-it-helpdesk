"""Configure the shared LangChain LLM cache.

``REDIS_URL`` is preferred because it works with any Redis-compatible service.
Upstash REST credentials remain a serverless-friendly fallback.
"""
from __future__ import annotations

import logging
from urllib.parse import urlsplit

from langchain_community.cache import UpstashRedisCache
from langchain_core.globals import set_llm_cache

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_cache_initialized: bool = False
_cache_backend: str = "none"
_cache_host: str | None = None


def _safe_host(url: str) -> str | None:
    """Return a credential-free host label for logs and health checks."""
    try:
        parsed = urlsplit(url)
        if not parsed.hostname:
            return None
        return f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
    except ValueError:
        return None


def _init_redis_url_cache() -> bool:
    """Initialize a cache through the standard Redis protocol."""
    global _cache_backend, _cache_host

    if not settings.redis_url:
        return False

    host = _safe_host(settings.redis_url)
    try:
        from langchain_community.cache import RedisCache
        from redis import Redis

        redis_client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        redis_client.ping()
        set_llm_cache(RedisCache(redis_=redis_client, ttl=settings.redis_cache_ttl))
        _cache_backend = "redis"
        _cache_host = host
        logger.info("[Cache] Redis LLM cache enabled at %s (TTL=%ds)", host, settings.redis_cache_ttl)
        return True
    except ImportError:
        logger.error("[Cache] REDIS_URL is set but package 'redis' is not installed")
    except Exception as exc:
        logger.warning(
            "[Cache] Redis connection failed at %s (%s)",
            host,
            type(exc).__name__,
        )
    return False


def _init_upstash_rest_cache() -> bool:
    """Initialize the Upstash REST fallback cache."""
    global _cache_backend, _cache_host

    url = settings.upstash_redis_rest_url
    token = settings.upstash_redis_rest_token
    if not url or not token:
        return False

    host = _safe_host(url)
    try:
        from upstash_redis import Redis

        redis_client = Redis(url=url, token=token)
        redis_client.ping()
        set_llm_cache(
            UpstashRedisCache(redis_=redis_client, ttl=settings.redis_cache_ttl)
        )
        _cache_backend = "upstash_rest"
        _cache_host = host
        logger.info(
            "[Cache] Upstash REST LLM cache enabled at %s (TTL=%ds)",
            host,
            settings.redis_cache_ttl,
        )
        return True
    except ImportError:
        logger.error("[Cache] Upstash credentials are set but package 'upstash-redis' is not installed")
    except Exception as exc:
        logger.warning(
            "[Cache] Upstash REST connection failed at %s (%s)",
            host,
            type(exc).__name__,
        )
    return False


def init_llm_cache() -> bool:
    """Initialize the cache without making Redis a startup dependency.

    Standard Redis is attempted first. If it is unavailable, Upstash REST is
    attempted before the application continues without a cache.
    """
    global _cache_initialized

    if _cache_initialized:
        return True

    if _init_redis_url_cache() or _init_upstash_rest_cache():
        _cache_initialized = True
        return True

    logger.warning(
        "[Cache] No usable Redis configuration; LLM requests will bypass cache"
    )
    return False


def get_cache_status() -> dict:
    """Return a credential-free cache status for the health endpoint."""
    return {
        "cache_enabled": _cache_initialized,
        "backend": _cache_backend,
        "host": _cache_host,
        "ttl_seconds": settings.redis_cache_ttl if _cache_initialized else None,
    }
