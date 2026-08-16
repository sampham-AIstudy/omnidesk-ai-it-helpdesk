"""
Rate Limiter Module
Implements sliding-window rate limiting per user/IP/session using config values.
RATE_LIMIT_MAX_REQUESTS=10, RATE_LIMIT_WINDOW_SECONDS=60.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Any, Dict

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_request_history = defaultdict(deque)


def is_rate_limited(identifier: str) -> Dict[str, Any]:
    """Check if identifier exceeds rate limit."""
    max_requests = settings.rate_limit_max_requests
    window_seconds = settings.rate_limit_window_seconds

    now = time.time()
    history = _request_history[identifier]

    # Remove timestamps outside sliding window
    while history and history[0] <= now - window_seconds:
        history.popleft()

    if len(history) >= max_requests:
        logger.warning(f"Rate limit exceeded for {identifier}: {len(history)} requests in {window_seconds}s")
        return {
            "allowed": False,
            "decision": "BLOCK",
            "reason": f"Rate limit exceeded ({max_requests} requests per {window_seconds}s)",
            "current_count": len(history),
        }

    history.append(now)
    return {
        "allowed": True,
        "decision": "ALLOW",
        "current_count": len(history),
    }


def reset_rate_limiter() -> None:
    """Reset rate limiter state (useful for tests)."""
    _request_history.clear()
