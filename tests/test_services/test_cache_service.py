"""Tests for Redis cache selection and secret-safe status reporting."""
from __future__ import annotations

import sys
from types import ModuleType

import pytest

from src.services import cache_service


@pytest.fixture(autouse=True)
def reset_cache_state(monkeypatch):
    monkeypatch.setattr(cache_service, "_cache_initialized", False)
    monkeypatch.setattr(cache_service, "_cache_backend", "none")
    monkeypatch.setattr(cache_service, "_cache_host", None)
    monkeypatch.setattr(cache_service.settings, "redis_url", "")
    monkeypatch.setattr(cache_service.settings, "upstash_redis_rest_url", "")
    monkeypatch.setattr(cache_service.settings, "upstash_redis_rest_token", "")


def test_cache_is_optional_when_no_credentials_are_configured():
    assert cache_service.init_llm_cache() is False
    assert cache_service.get_cache_status() == {
        "cache_enabled": False,
        "backend": "none",
        "host": None,
        "ttl_seconds": None,
    }


def test_redis_url_is_preferred_and_credentials_are_redacted(monkeypatch):
    clients = []

    class FakeRedis:
        @classmethod
        def from_url(cls, url, **kwargs):
            instance = cls()
            instance.url = url
            instance.options = kwargs
            clients.append(instance)
            return instance

        def ping(self):
            return True

    redis_module = ModuleType("redis")
    redis_module.Redis = FakeRedis
    monkeypatch.setitem(sys.modules, "redis", redis_module)

    import langchain_community.cache as langchain_cache

    cache_instances = []
    monkeypatch.setattr(
        langchain_cache,
        "RedisCache",
        lambda redis_, ttl: cache_instances.append((redis_, ttl)) or object(),
    )
    configured_caches = []
    monkeypatch.setattr(cache_service, "set_llm_cache", configured_caches.append)
    monkeypatch.setattr(
        cache_service.settings,
        "redis_url",
        "rediss://user:super-secret@cache.example.com:6380/0",
    )

    assert cache_service.init_llm_cache() is True
    assert clients[0].options == {
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
    }
    assert cache_instances[0][1] == cache_service.settings.redis_cache_ttl
    assert len(configured_caches) == 1
    assert cache_service.get_cache_status() == {
        "cache_enabled": True,
        "backend": "redis",
        "host": "cache.example.com:6380",
        "ttl_seconds": cache_service.settings.redis_cache_ttl,
    }
    assert "super-secret" not in repr(cache_service.get_cache_status())


def test_upstash_rest_is_used_when_standard_redis_fails(monkeypatch):
    class FailingRedis:
        @classmethod
        def from_url(cls, url, **kwargs):
            raise ConnectionError("unavailable")

    redis_module = ModuleType("redis")
    redis_module.Redis = FailingRedis
    monkeypatch.setitem(sys.modules, "redis", redis_module)

    class FakeUpstashRedis:
        def __init__(self, url, token):
            self.url = url
            self.token = token

        def ping(self):
            return "PONG"

    upstash_module = ModuleType("upstash_redis")
    upstash_module.Redis = FakeUpstashRedis
    monkeypatch.setitem(sys.modules, "upstash_redis", upstash_module)
    monkeypatch.setattr(cache_service, "UpstashRedisCache", lambda redis_, ttl: object())
    monkeypatch.setattr(cache_service, "set_llm_cache", lambda cache: None)
    monkeypatch.setattr(cache_service.settings, "redis_url", "redis://cache:6379/0")
    monkeypatch.setattr(
        cache_service.settings,
        "upstash_redis_rest_url",
        "https://rest-cache.example.com",
    )
    monkeypatch.setattr(cache_service.settings, "upstash_redis_rest_token", "token")

    assert cache_service.init_llm_cache() is True
    assert cache_service.get_cache_status()["backend"] == "upstash_rest"
    assert cache_service.get_cache_status()["host"] == "rest-cache.example.com"
