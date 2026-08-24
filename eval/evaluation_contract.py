"""Versioned lock validation for reproducible evaluation inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonicalize_text_bytes(data: bytes) -> bytes:
    """Normalize line endings (CRLF, lone CR -> LF) for cross-platform text hashing."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_text_file(path: Path) -> str:
    """Compute SHA-256 over line-ending normalized text bytes."""
    data = canonicalize_text_bytes(path.read_bytes())
    return hashlib.sha256(data).hexdigest()


def sha256_file_bytes(path: Path) -> str:
    """Compute SHA-256 over raw file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file(path: Path) -> str:
    """Canonical text hashing for evaluation text files by default."""
    return sha256_text_file(path)


def load_lock(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_lock(root: Path, lock: dict[str, Any]) -> list[str]:
    """Return mismatches; callers must fail before an LLM call when non-empty."""
    errors: list[str] = []
    for key in ("golden", "manifest", "source_mapping", "context_snapshot", "knowledge_base_fixture", "ticket_fixture"):
        if key not in lock:
            continue
        item = lock[key]
        path = root / item["path"]
        if not path.exists():
            errors.append(f"LOCKED_FILE_MISSING:{key}")
        elif sha256_text_file(path) != item["sha256"]:
            errors.append(f"LOCK_HASH_MISMATCH:{key}")
    canonical = lock["routing_contract_ids"]
    if len(canonical) != 21 or len(set(canonical)) != 21:
        errors.append("INVALID_CANONICAL_ROUTING_CONTRACT")
    return errors
