"""Runtime version and build identification for Help Desk AI Agent."""
from __future__ import annotations

import hashlib
import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

APP_VERSION = "1.0.0"
GUARDRAILS_VERSION = "1.2.0"
BEHAVIOR_CONTRACT_VERSION = "1.0.0"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MANIFEST_PATH = _PROJECT_ROOT / "eval" / "behavior" / "chat_behavior_manifest.json"


@lru_cache(maxsize=1)
def get_git_commit() -> str:
    """Retrieve short git commit SHA or environment fallback."""
    env_sha = os.environ.get("BUILD_COMMIT") or os.environ.get("GIT_COMMIT")
    if env_sha:
        return env_sha[:8]
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "dev-local"


@lru_cache(maxsize=1)
def get_behavior_manifest_hash() -> str:
    """Compute sha256 digest of the behavior manifest for deployment verification."""
    if _MANIFEST_PATH.exists():
        try:
            content = _MANIFEST_PATH.read_bytes()
            return hashlib.sha256(content).hexdigest()[:12]
        except Exception:
            pass
    return "unknown"


def get_build_info() -> dict[str, Any]:
    """Return non-sensitive runtime build and policy version information."""
    from src.config import get_settings

    settings = get_settings()
    return {
        "app_version": APP_VERSION,
        "guardrails_version": GUARDRAILS_VERSION,
        "behavior_contract_version": BEHAVIOR_CONTRACT_VERSION,
        "git_commit": get_git_commit(),
        "manifest_hash": get_behavior_manifest_hash(),
        "app_env": settings.app_env,
        "llm_provider": getattr(settings, "llm_provider", "mistral"),
    }
