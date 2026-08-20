"""Request size limiting ASGI middleware.

Enforces hard maximum request body size limits before downstream routing,
RAG, or LLM execution.
"""
from __future__ import annotations

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Maximum request body limits (in bytes)
MAX_CHAT_REQUEST_BYTES = 65_536       # 64 KB for chat endpoints
MAX_GENERAL_REQUEST_BYTES = 1_048_576  # 1 MB for general endpoints

_CHAT_PATHS = (
    "/api/v1/chat",
    "/api/v1/tickets/",
)


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        method: str = scope.get("method", "GET")

        # Only check mutation methods
        if method in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        is_chat_path = any(p in path for p in ("/api/v1/chat", "/messages"))
        max_bytes = MAX_CHAT_REQUEST_BYTES if is_chat_path else MAX_GENERAL_REQUEST_BYTES

        # 1. Fast check Content-Length header if present
        content_length_header = headers.get("content-length")
        if content_length_header is not None:
            try:
                content_length = int(content_length_header)
                if content_length > max_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "error": "INPUT_TOO_LARGE",
                            "detail": f"Kích thước yêu cầu vượt quá giới hạn cho phép ({max_bytes} bytes).",
                        },
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        # 2. Wrap receive to stream and count body chunks (handles chunked transfer & missing header)
        received_bytes = 0

        async def receive_with_size_limit() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                received_bytes += len(chunk)
                if received_bytes > max_bytes:
                    raise PayloadTooLargeError(max_bytes)
            return message

        try:
            await self.app(scope, receive_with_size_limit, send)
        except PayloadTooLargeError:
            response = JSONResponse(
                status_code=413,
                content={
                    "error": "INPUT_TOO_LARGE",
                    "detail": f"Kích thước nội dung gửi lên vượt quá giới hạn ({max_bytes} bytes).",
                },
            )
            await response(scope, receive, send)


class PayloadTooLargeError(Exception):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"Payload exceeds {max_bytes} bytes")
        self.max_bytes = max_bytes
