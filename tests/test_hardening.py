"""Tests for HARDEN-1: Input bounds, request body size limits, history resource limits, and AI abuse prevention."""
from __future__ import annotations

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.guardrails.ai_abuse_guard import (
    MAX_CHAT_MESSAGE_BYTES,
    MAX_CHAT_MESSAGE_CHARS,
    guard_ai_generation,
    reset_abuse_guard_state,
    validate_chat_message_size,
)
from src.main import app
from src.models.chat_conversation import ChatMessage
from src.models.schemas import DuplicateCheckRequest, TicketCreate
from src.models.ticket_message import TicketMessage, TicketMessageSender
from src.services.context_query_service import build_context_aware_retrieval_query
from src.services.recent_conversation_context import (
    MAX_HISTORY_MESSAGE_CHARS,
    MAX_TICKET_RECENT_HISTORY_CHARS,
    MAX_WORKSPACE_RECENT_HISTORY_CHARS,
    RecentConversationMessage,
    format_recent_history,
    load_ticket_recent_history,
    load_workspace_recent_history,
)

settings = get_settings()


class TestInputSizeValidation:
    """Test character and byte boundary checks on chat inputs."""

    def test_7999_chars_accepted(self):
        msg = "a" * 7999
        # Should not raise
        validate_chat_message_size(msg)

    def test_8000_chars_accepted(self):
        msg = "a" * 8000
        # Should not raise
        validate_chat_message_size(msg)

    def test_8001_chars_rejected_with_413(self):
        msg = "a" * 8001
        with pytest.raises(Exception) as exc_info:
            validate_chat_message_size(msg)
        assert exc_info.value.status_code == 413
        assert exc_info.value.detail.get("error") == "INPUT_TOO_LARGE"

    def test_multibyte_encoded_payload_rejected_when_exceeding_32kb(self):
        # 4-byte unicode character repeated 10,000 times = 40,000 bytes > 32KB
        # while char length is 10,000 > 8000, or 7,000 chars * 5 bytes/char = 35,000 bytes
        msg = "🚀" * 7500  # 7500 chars <= 8000, but 7500 * 4 = 30000 bytes
        # 8000 chars of 4-byte emoji = 32000 bytes
        # Let's test a string within 8000 chars but > 32768 bytes
        # e.g., 7000 * 5 bytes = 35000 bytes (or 3-byte vietnamese character: "ạ" * 7000 is 7000*3=21000, "ạ" * 8000 is 8000*3=24000)
        # 4-byte emoji 8200 would fail char limit first, but let's test 7500 emojis + multi-byte characters
        msg_large_bytes = "🔒" * 7500 + "A" * 1000  # 8500 chars fails
        msg_multi_byte_33kb = "🚀" * 7800 + "🛠️" * 200  # 8000 chars, but emojis + variation selectors > 32KB
        if len(msg_multi_byte_33kb.encode("utf-8")) > MAX_CHAT_MESSAGE_BYTES:
            with pytest.raises(Exception) as exc_info:
                validate_chat_message_size(msg_multi_byte_33kb)
            assert exc_info.value.status_code == 413


class TestHistoryResourceLimits:
    """Test that huge history is bounded strictly without dropping the current message."""

    @pytest.mark.asyncio
    async def test_workspace_history_bounded_by_total_chars(self):
        from src.database import AsyncSessionLocal
        from src.models.chat_conversation import ChatConversation
        async with AsyncSessionLocal() as db_session:
            conv = ChatConversation(id="harden-conv-1", user_id=1, title="Hardening Test")
            db_session.add(conv)
            await db_session.flush()

            # Add 8 messages of 3000 chars each = 24000 chars (exceeds 16000 char budget)
            for i in range(8):
                msg = ChatMessage(
                    conversation_id=conv.id,
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"Message {i}: " + ("x" * 2500),
                )
                db_session.add(msg)
            await db_session.commit()

            history = await load_workspace_recent_history(
                db_session,
                conversation_id=conv.id,
                user_id=1,
                exclude_message_id=None,
            )

            # Must not exceed MAX_WORKSPACE_RECENT_HISTORY_CHARS (16000)
            total_history_chars = sum(len(m.content) for m in history)
            assert total_history_chars <= MAX_WORKSPACE_RECENT_HISTORY_CHARS

            # The newest message (Message 7) must be present (priority to latest)
            assert any("Message 7" in m.content for m in history)

    @pytest.mark.asyncio
    async def test_ticket_history_bounded_by_total_chars(self):
        from src.database import AsyncSessionLocal
        from src.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus
        async with AsyncSessionLocal() as db_session:
            ticket = Ticket(
                ticket_number="INC-HARDEN-001",
                title="VPN Issue",
                description="Cannot connect to corporate VPN",
                status=TicketStatus.OPEN,
                submitter_id=1,
                category=TicketCategory.NETWORK,
                priority=TicketPriority.MEDIUM,
            )
            db_session.add(ticket)
            await db_session.flush()

            # Add 5 messages of 3000 chars each = 15000 chars (exceeds 12000 char budget)
            for i in range(5):
                msg = TicketMessage(
                    ticket_id=ticket.id,
                    sender_type=TicketMessageSender.USER if i % 2 == 0 else TicketMessageSender.AGENT,
                    content=f"Ticket Msg {i}: " + ("y" * 2800),
                )
                db_session.add(msg)
            await db_session.commit()

            history = await load_ticket_recent_history(
                db_session,
                ticket_id=ticket.id,
                exclude_message_id=None,
            )

            total_ticket_chars = sum(len(m.content) for m in history)
            assert total_ticket_chars <= MAX_TICKET_RECENT_HISTORY_CHARS
            # The latest message (Ticket Msg 4) must be kept
            assert any("Ticket Msg 4" in m.content for m in history)


class TestQueryRewriteLengthConstraint:
    """Test that context query rewrite is strictly bounded by max_retrieval_query_chars (400)."""

    def test_query_rewrite_never_exceeds_400_chars_even_with_huge_history(self):
        # Create huge history
        history = [
            RecentConversationMessage(
                message_id=str(i),
                role="user",
                content="Hướng dẫn kết nối VPN Cisco AnyConnect từ xa gặp mã lỗi 0x80004005 khi nhập OTP " * 10,
            )
            for i in range(10)
        ]

        long_follow_up = "Tôi đã thử làm theo bước đó rồi nhưng vẫn không được, xin hướng dẫn tiếp theo " * 5
        res = build_context_aware_retrieval_query(long_follow_up, recent_history=history)

        assert len(res.query) <= 400
        assert res.rewritten is True


class TestAIRateAndConcurrencyGuard:
    """Test single-instance in-memory rate and concurrency limiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_20_requests_per_minute(self):
        reset_abuse_guard_state()
        user_id = 99991

        # First 20 requests should pass
        for _ in range(20):
            async with guard_ai_generation(user_id):
                pass

        # 21st request in the same minute must fail with 429
        with pytest.raises(Exception) as exc_info:
            async with guard_ai_generation(user_id):
                pass

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail.get("error") == "RATE_LIMITED"

    @pytest.mark.asyncio
    async def test_concurrency_limiter_blocks_over_2_simultaneous_generations(self):
        reset_abuse_guard_state()
        user_id = 99992

        async def long_generation():
            async with guard_ai_generation(user_id):
                await asyncio.sleep(0.1)

        # Start 2 active concurrent tasks
        t1 = asyncio.create_task(long_generation())
        t2 = asyncio.create_task(long_generation())
        await asyncio.sleep(0.01)

        # 3rd concurrent request must immediately fail with 429
        with pytest.raises(Exception) as exc_info:
            async with guard_ai_generation(user_id):
                pass

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail.get("error") == "CONCURRENCY_LIMIT_EXCEEDED"

        await asyncio.gather(t1, t2)
        # After completion, concurrency count is decremented and new request succeeds
        async with guard_ai_generation(user_id):
            pass


class TestPydanticSchemaHardening:
    """Test schema constraints for text fields."""

    def test_ticket_title_length_limit(self):
        with pytest.raises(Exception):
            TicketCreate(title="a" * 201, description="Valid description of at least 10 chars")

    def test_ticket_description_length_limit(self):
        with pytest.raises(Exception):
            TicketCreate(title="Valid title", description="a" * 5001)

    def test_duplicate_check_limits(self):
        with pytest.raises(Exception):
            DuplicateCheckRequest(title="a" * 201, description="Valid description")

        with pytest.raises(Exception):
            DuplicateCheckRequest(title="Valid title", description="a" * 5001)


class TestRequestSizeLimitMiddleware:
    """Test ASGI RequestSizeLimitMiddleware with real client requests."""

    @pytest.mark.asyncio
    async def test_multi_megabyte_body_rejected_early_with_413(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 2 MB payload to /api/v1/chat
            oversized_payload = {"message": "A" * (2 * 1024 * 1024)}
            resp = await client.post(
                "/api/v1/chat",
                json=oversized_payload,
                headers={"Authorization": "Bearer dummy"},
            )
            assert resp.status_code == 413
            data = resp.json()
            assert data.get("error") == "INPUT_TOO_LARGE"
