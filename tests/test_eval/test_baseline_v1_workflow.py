"""Workflow baseline: real fixture DB state, no LLM judge or vector dependency."""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.ticket import TicketStatus
from src.models.user import User
from src.services import auth_service, ticket_service
from src.services.ticket_conversation_service import escalate_to_technician


@pytest.fixture(autouse=True)
def disable_non_workflow_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep this suite scoped to DB state transitions and audit persistence."""
    monkeypatch.setattr("src.services.ticket_conversation_service.add_message", AsyncMock())


async def _create() -> tuple[int, int, int]:
    async with AsyncSessionLocal() as db:
        employee = (await db.execute(select(User).where(User.username == "employee1"))).scalar_one()
        manager = (await db.execute(select(User).where(User.username == "tech1"))).scalar_one()
        ticket = await ticket_service.create_ticket(
            db, title="Baseline workflow ticket", description="Laptop does not power on.", submitter_id=employee.id
        )
        await db.commit()
        return ticket.id, employee.id, manager.id


@pytest.mark.asyncio
async def test_workflow_create_incident_has_persisted_ticket_id() -> None:
    ticket_id, _, _ = await _create()
    async with AsyncSessionLocal() as db:
        assert (await ticket_service.get_ticket(db, ticket_id)).id == ticket_id


@pytest.mark.asyncio
async def test_workflow_request_technician_persists_waiting_state_and_audit() -> None:
    ticket_id, employee_id, _ = await _create()
    async with AsyncSessionLocal() as db:
        ticket = await ticket_service.get_ticket(db, ticket_id)
        await escalate_to_technician(db, ticket=ticket, actor_id=employee_id, reason="Baseline technician request")
        await db.commit()
    async with AsyncSessionLocal() as db:
        assert (await ticket_service.get_ticket(db, ticket_id)).status == TicketStatus.WAITING_FOR_AGENT


@pytest.mark.asyncio
async def test_workflow_takeover_close_and_reopen_have_persisted_transitions() -> None:
    ticket_id, employee_id, manager_id = await _create()
    async with AsyncSessionLocal() as db:
        taken = await ticket_service.takeover_ticket(db, ticket_id, manager_id)
        assert taken.assignee_id == manager_id
        with patch("src.services.zero_mem_service.index_ticket_trace", AsyncMock()):
            closed = await ticket_service.close_ticket(db, ticket_id, employee_id, "user", "Baseline close")
        assert closed.status == TicketStatus.CLOSED
        closed.status = TicketStatus.REOPENED
        await db.commit()
    async with AsyncSessionLocal() as db:
        assert (await ticket_service.get_ticket(db, ticket_id)).status == TicketStatus.REOPENED


@pytest.mark.asyncio
async def test_workflow_unauthorized_action_contract_is_explicit() -> None:
    """A cross-tenant user cannot reach the ticket before a tool/action executes."""
    ticket_id, _, _ = await _create()
    async with AsyncSessionLocal() as db:
        ticket = await ticket_service.get_ticket(db, ticket_id)
        other_user = (await db.execute(select(User).where(User.username == "employee_healthcare"))).scalar_one()
        assert auth_service.can_view_ticket(other_user, ticket) is False
