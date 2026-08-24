from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.ticket import Ticket
from src.models.user import User
from src.services.ticket_service import create_ticket


@pytest.mark.asyncio
async def test_ticket_number_collision_retries_against_database_constraint():
    """A collision is recovered by the DB-authoritative bounded retry path."""
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).order_by(User.id))).scalars().first()
        assert user is not None
        with patch(
            "src.services.ticket_service._gen_ticket_number",
            side_effect=["INC-TEST-1000", "INC-TEST-1000", "INC-TEST-1001"],
        ):
            first = await create_ticket(db, "First", "First collision fixture", user.id)
            second = await create_ticket(db, "Second", "Second collision fixture", user.id)

        assert first.ticket_number == "INC-TEST-1000"
        assert second.ticket_number == "INC-TEST-1001"
        assert (await db.execute(select(Ticket).where(Ticket.ticket_number == "INC-TEST-1001"))).scalar_one().id == second.id
