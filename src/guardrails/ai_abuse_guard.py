"""AI request abuse prevention: input bounds, rate limiting, and concurrency guards."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import HTTPException

# Authoritative input limits
MAX_CHAT_MESSAGE_CHARS = 8000
MAX_CHAT_MESSAGE_BYTES = 32_768  # 32 KB

# Rate & Concurrency limits
MAX_AI_REQUESTS_PER_MINUTE = 20
AI_RATE_LIMIT_WINDOW_SECONDS = 60
MAX_CONCURRENT_AI_GENERATIONS_PER_USER = 2

# In-memory tracking structures (per-process, zero Redis dependency required)
_user_request_timestamps: dict[int, deque[float]] = defaultdict(deque)
_user_active_generations: dict[int, int] = defaultdict(int)
_lock = asyncio.Lock()


def validate_chat_message_size(message: str) -> None:
    """Authoritative backend validation for chat message text length and encoded byte size.

    Must be invoked before any Routing, Embedding, RAG, ZeroMem, Query Rewrite, or LLM call.
    Raises HTTP 413 INPUT_TOO_LARGE if limits are exceeded.
    """
    if len(message) > MAX_CHAT_MESSAGE_CHARS:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "INPUT_TOO_LARGE",
                "detail": f"Nội dung tin nhắn vượt quá giới hạn {MAX_CHAT_MESSAGE_CHARS} ký tự ({len(message)} ký tự).",
            },
        )

    encoded_bytes = len(message.encode("utf-8"))
    if encoded_bytes > MAX_CHAT_MESSAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "INPUT_TOO_LARGE",
                "detail": f"Kích thước nội dung tin nhắn vượt quá giới hạn {MAX_CHAT_MESSAGE_BYTES} bytes ({encoded_bytes} bytes).",
            },
        )


@asynccontextmanager
async def guard_ai_generation(user_id: int) -> AsyncGenerator[None, None]:
    """Context manager protecting AI generation endpoints against rate and concurrency abuse.

    Enforces:
    1. 20 AI requests / minute / authenticated user -> HTTP 429
    2. Max 2 concurrent AI generations / authenticated user -> HTTP 429
    """
    now = time.time()

    async with _lock:
        # 1. Check Rate Limit (Sliding Window)
        history = _user_request_timestamps[user_id]
        while history and history[0] <= now - AI_RATE_LIMIT_WINDOW_SECONDS:
            history.popleft()

        if len(history) >= MAX_AI_REQUESTS_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "RATE_LIMITED",
                    "detail": f"Bạn đã đạt giới hạn {MAX_AI_REQUESTS_PER_MINUTE} yêu cầu AI mỗi phút. Vui lòng thử lại sau.",
                },
            )

        # 2. Check Concurrency Limit
        active = _user_active_generations[user_id]
        if active >= MAX_CONCURRENT_AI_GENERATIONS_PER_USER:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "CONCURRENCY_LIMIT_EXCEEDED",
                    "detail": f"Bạn đang có tối đa {MAX_CONCURRENT_AI_GENERATIONS_PER_USER} yêu cầu AI đang xử lý đồng thời. Vui lòng chờ hoàn tất.",
                },
            )

        # Record this request & increment active concurrency
        history.append(now)
        _user_active_generations[user_id] = active + 1

    try:
        yield
    finally:
        async with _lock:
            if _user_active_generations[user_id] > 0:
                _user_active_generations[user_id] -= 1


def reset_abuse_guard_state() -> None:
    """Helper for testing to reset rate and concurrency counters."""
    _user_request_timestamps.clear()
    _user_active_generations.clear()
