from types import SimpleNamespace

from src.services import llm


def test_gemini_fallback_uses_only_the_dedicated_key(monkeypatch):
    monkeypatch.setattr(llm, "settings", SimpleNamespace(gemini_api_key="gemini-fallback-key"))
    monkeypatch.setenv("GEMINI_API_KEY", "environment-gemini-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "guardrail-only-key")

    assert llm.get_gemini_api_key() == "gemini-fallback-key"


def test_gemini_fallback_does_not_use_google_guardrail_key(monkeypatch):
    monkeypatch.setattr(llm, "settings", SimpleNamespace(gemini_api_key=""))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "guardrail-only-key")

    assert llm.get_gemini_api_key() == ""
