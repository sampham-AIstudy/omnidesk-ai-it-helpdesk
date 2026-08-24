"""Canonical Vietnam time helpers for identifiers and user-facing timestamps."""
from datetime import datetime
from zoneinfo import ZoneInfo

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def vietnam_now() -> datetime:
    return datetime.now(VIETNAM_TZ)
