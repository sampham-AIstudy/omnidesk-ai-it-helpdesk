"""
AI Logger for Web App — Tự động ghi lại các lượt gọi AI Agent (Classifier, RAG, LLM)
vào `.ai-log/session.jsonl` để đẩy lên server https://phoenix.note.transformerlabs.ai/ai-logs
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
VN_TZ = timezone(timedelta(hours=7))


def _git_output(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


from functools import lru_cache

@lru_cache(maxsize=1)
def _get_cached_git_info() -> dict:
    """Cache Git metadata once to avoid spawning 4 subprocesses on every AI log event."""
    origin = _git_output("git remote get-url origin")
    repo = origin.rstrip("/").split("/")[-1] if origin else "P-236"
    if repo.endswith(".git"):
        repo = repo[:-4]
    return {
        "repo": repo,
        "branch": _git_output("git rev-parse --abbrev-ref HEAD") or "main",
        "commit": _git_output("git rev-parse --short HEAD") or "local",
        "student": _git_output("git config user.email") or "student@corp.example.com",
    }


def log_web_app_ai_event(
    event_name: str,
    prompt: str,
    response_summary: str,
    model: str = "mistral-large-latest",
    session_id: str = "",
    tool: str = "helpdesk-agent",
):
    """Ghi nhận 1 sự kiện AI của Web App vào .ai-log/session.jsonl."""
    try:
        git_info = _get_cached_git_info()
        entry = {
            "ts": datetime.now(VN_TZ).isoformat(),
            "tool": tool,
            "event": event_name,
            "session_id": session_id or "web-session",
            "model": model,
            "repo": git_info["repo"],
            "branch": git_info["branch"],
            "commit": git_info["commit"],
            "student": git_info["student"],
            "prompt": prompt[:1000] if prompt else "",
            "response_summary": response_summary[:500] if response_summary else "",
        }


        log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "session.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(f"[AI-Logger] Logged web app AI event: {event_name}")

    except Exception as e:
        logger.warning(f"[AI-Logger] Failed to log web app AI event: {e}")
