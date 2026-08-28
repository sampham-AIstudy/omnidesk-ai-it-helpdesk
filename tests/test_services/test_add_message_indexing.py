"""Unit tests for add_message memory indexing behavior."""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ticket_message import TicketMessageSender
from src.services.ticket_conversation_service import add_message


@pytest.mark.asyncio
async def test_add_message_indexes_visible_message():
    db = AsyncMock(spec=AsyncSession)
    with patch("src.services.zero_mem_service.index_message_by_id", new_callable=AsyncMock) as mock_index:
        await add_message(
            db,
            ticket_id=1,
            sender_type=TicketMessageSender.USER,
            content="Xin chào",
            is_internal=False,
            index_for_memory=True,
        )
        assert db.add.called
        assert db.flush.called
        assert db.refresh.called
        assert mock_index.await_count == 1


@pytest.mark.asyncio
async def test_add_message_skips_internal_notes():
    db = AsyncMock(spec=AsyncSession)
    with patch("src.services.zero_mem_service.index_message_by_id", new_callable=AsyncMock) as mock_index:
        await add_message(
            db,
            ticket_id=1,
            sender_type=TicketMessageSender.TECHNICIAN,
            content="Ghi chú nội bộ kỹ thuật",
            is_internal=True,
            index_for_memory=True,
        )
        assert db.add.called
        assert mock_index.await_count == 0
