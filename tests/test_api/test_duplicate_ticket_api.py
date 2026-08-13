from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from unittest.mock import AsyncMock, patch

import pytest

from src.database import AsyncSessionLocal
from src.models.ticket import Ticket, TicketStatus
from src.services.duplicate_detection_service import DuplicateCheck, DuplicateClass, DuplicateMatch

_sequence = count(1)


async def _active_match() -> DuplicateCheck:
    async with AsyncSessionLocal() as db:
        ticket = Ticket(
            ticket_number=f"INC-DUP-{next(_sequence):03d}", title="[VPN] Không kết nối được VPN", description="Lỗi SSL VPN 809",
            submitter_id=1, status=TicketStatus.IN_PROGRESS, created_at=datetime.now(UTC),
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        match = DuplicateMatch(
            ticket=ticket, classification=DuplicateClass.SEMANTIC, score=0.93,
            method="semantic_vector_hybrid", title_score=0.92, semantic_score=0.94,
            is_active=True, is_resolved=False, solution=None,
        )
        return DuplicateCheck("vpn", "vpn 809", [match], 1, False)


@pytest.mark.asyncio
async def test_high_confidence_duplicate_is_created_without_interrupting_submit(client, auth_employee):
    check = await _active_match()
    with (
        patch("src.services.duplicate_detection_service.check_duplicate_tickets", AsyncMock(return_value=check)),
        patch("src.services.duplicate_detection_service.index_ticket_for_duplicate_detection"),
        patch("src.api.tickets._run_agent_workflow", AsyncMock()),
    ):
        response = await client.post(
            "/api/v1/tickets",
            json={"title": "Không kết nối được VPN", "description": "Lỗi SSL VPN 809"},
            headers={"Authorization": f"Bearer {auth_employee}"},
        )

    assert response.status_code == 201
    async with AsyncSessionLocal() as db:
        created = await db.get(Ticket, response.json()["ticket_id"])
        assert created is not None
        assert created.duplicate_of_ticket_id == check.primary.ticket.id
        assert created.duplicate_confirmed_by is None


@pytest.mark.asyncio
async def test_user_can_create_anyway_and_duplicate_link_is_persisted(client, auth_employee):
    check = await _active_match()
    with (
        patch("src.services.duplicate_detection_service.check_duplicate_tickets", AsyncMock(return_value=check)),
        patch("src.services.duplicate_detection_service.index_ticket_for_duplicate_detection"),
        patch("src.api.tickets._run_agent_workflow", AsyncMock()),
    ):
        response = await client.post(
            "/api/v1/tickets",
            json={
                "title": "Không kết nối được VPN", "description": "Lỗi SSL VPN 809",
            },
            headers={"Authorization": f"Bearer {auth_employee}"},
        )

    assert response.status_code == 201
    ticket_id = response.json()["ticket_id"]
    async with AsyncSessionLocal() as db:
        created = await db.get(Ticket, ticket_id)
        assert created is not None
        assert created.duplicate_of_ticket_id == check.primary.ticket.id
        assert created.duplicate_score == pytest.approx(0.93)
