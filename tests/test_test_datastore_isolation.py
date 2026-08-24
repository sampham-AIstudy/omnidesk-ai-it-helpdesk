from __future__ import annotations

from pathlib import Path

from src.config import get_settings
from src.database import engine
from src.services import rag_service


def test_pytest_uses_only_test_owned_sqlite_and_chroma_paths():
    settings = get_settings()
    root = Path(__file__).resolve().parents[1]

    assert Path(str(engine.url.database)).resolve() == (root / "data" / "test.db").resolve()
    assert Path(settings.chroma_persist_dir).resolve() == (root / "data" / "test_chroma").resolve()
    assert Path(rag_service.settings.chroma_persist_dir).resolve() == (root / "data" / "test_chroma").resolve()
    assert settings.chroma_collection_name == "helpdesk_kb_multilingual_v3_sentence_transformer"
