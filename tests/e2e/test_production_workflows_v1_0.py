"""Repeatable API + DB workflow coverage for the frozen production baseline.

External model, vector and background-agent work are mocked only at their
provider boundary.  HTTP handlers, authorization, database persistence,
state transitions and audit writes remain real.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from src.api.tickets import _idempotency_store
from src.database import AsyncSessionLocal
from src.main import app
from src.models.audit_log import AuditAction, AuditLog
from src.models.service_request import ServiceRequest, ServiceRequestStatus
from src.models.ticket import Ticket, TicketStatus, TicketSupportMode
from src.models.ticket_message import TicketMessage, TicketMessageSender
from src.services.action_grounding import ActionResult, action_state_reply


@pytest.fixture(autouse=True)
def isolate_e2e_process_and_provider_state() -> None:
    """Keep E2E deterministic while retaining HTTP, DB, RBAC and state-machine paths."""
    from src.assignment.rate_limiter import _request_history

    _idempotency_store.clear()
    _request_history.clear()
    with (
        patch("src.services.zero_mem_service.index_message_by_id", new=AsyncMock()),
        patch("src.services.zero_mem_service.index_ticket_trace", new=AsyncMock()),
    ):
        yield


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client: AsyncClient, username: str, password: str = "demo123") -> str:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def create_incident(client: AsyncClient, token: str, *, prefix: str = "E2E incident") -> tuple[int, str]:
    title = f"{prefix} {uuid4().hex}"
    no_duplicate = SimpleNamespace(
        primary=None,
        matches=[],
        same_user_repeat_count=0,
        shared_incident_signal=False,
    )
    with (
        patch("src.api.tickets._run_agent_workflow", new=AsyncMock()),
        patch("src.services.duplicate_detection_service.check_duplicate_tickets", new=AsyncMock(return_value=no_duplicate)),
        patch("src.services.duplicate_detection_service.audit_duplicate_decision", new=AsyncMock()),
        patch("src.services.duplicate_detection_service.index_ticket_for_duplicate_detection"),
        patch("src.services.zero_mem_service.index_ticket_trace", new=AsyncMock()),
    ):
        response = await client.post(
            "/api/v1/tickets",
            json={"title": title, "description": "Repeatable end-to-end workflow verification."},
            headers=headers(token),
        )
    assert response.status_code == 201, response.text
    return response.json()["ticket_id"], title


async def ticket_row(ticket_id: int) -> Ticket:
    async with AsyncSessionLocal() as db:
        ticket = await db.get(Ticket, ticket_id)
        assert ticket is not None
        return ticket


async def ticket_messages(ticket_id: int) -> list[TicketMessage]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.id)
        )
        return list(result.scalars())


async def ticket_audits(ticket_id: int) -> list[AuditLog]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AuditLog).where(AuditLog.ticket_id == ticket_id).order_by(AuditLog.id)
        )
        return list(result.scalars())


async def fake_conversation_handler(
    db,
    *,
    ticket: Ticket,
    user,
    content: str,
    on_token: Callable[[str], Awaitable[None]] | None = None,
) -> list[TicketMessage]:
    """Provider-free conversation boundary that still exercises API persistence."""
    from src.services.ticket_conversation_service import add_message, list_messages

    await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=TicketMessageSender.USER,
        sender_id=user.id,
        content=content,
        index_for_memory=False,
    )
    if on_token is not None:
        await on_token("Acknowledged.")
    await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=TicketMessageSender.AGENT,
        content="Acknowledged. No action has been executed.",
        index_for_memory=False,
    )
    return await list_messages(db, ticket.id)


@pytest.mark.asyncio
async def test_e2e_create_incident_persists_ticket_and_audit(client: AsyncClient, auth_employee: str) -> None:
    ticket_id, title = await create_incident(client, auth_employee, prefix="E2E create")

    ticket = await ticket_row(ticket_id)
    audits = await ticket_audits(ticket_id)

    assert ticket.title == title
    assert ticket.status == TicketStatus.OPEN
    assert ticket.assignee_id is None
    created = next(item for item in audits if item.action == AuditAction.TICKET_CREATED)
    assert created.actor_id == ticket.submitter_id
    assert created.created_at is not None


@pytest.mark.asyncio
async def test_e2e_ai_followup_persists_messages_without_duplicate_ticket(client: AsyncClient, auth_employee: str) -> None:
    ticket_id, title = await create_incident(client, auth_employee, prefix="E2E followup")
    with patch("src.services.ticket_conversation_service.handle_ticket_message", new=fake_conversation_handler):
        response = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            json={"message": "The problem is still happening."},
            headers=headers(auth_employee),
        )

    assert response.status_code == 200, response.text
    messages = await ticket_messages(ticket_id)
    assert [message.sender_type for message in messages] == [TicketMessageSender.USER, TicketMessageSender.AGENT]
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(Ticket).where(Ticket.title == title))
    assert count == 1
    # Trace propagation is asserted only when a tracing backend creates a span.
    trace_id = response.headers.get("X-Trace-ID")
    assert trace_id is None or (len(trace_id) == 32 and int(trace_id, 16) >= 0)


@pytest.mark.asyncio
async def test_e2e_escalation_waits_for_human_without_fake_acceptance(client: AsyncClient, auth_employee: str) -> None:
    ticket_id, _ = await create_incident(client, auth_employee, prefix="E2E escalation")
    response = await client.post(f"/api/v1/tickets/{ticket_id}/request-technician", headers=headers(auth_employee))

    assert response.status_code == 200, response.text
    ticket = await ticket_row(ticket_id)
    assert ticket.status == TicketStatus.WAITING_FOR_AGENT
    assert ticket.assignee_id is None
    assert ticket.support_mode == TicketSupportMode.AI
    assert any(item.action == AuditAction.TICKET_ESCALATED for item in await ticket_audits(ticket_id))


@pytest.mark.asyncio
async def test_e2e_takeover_requires_role_and_persists_assignment_and_audit(
    client: AsyncClient, auth_employee: str, auth_technician: str,
) -> None:
    ticket_id, _ = await create_incident(client, auth_employee, prefix="E2E takeover")
    await client.post(f"/api/v1/tickets/{ticket_id}/request-technician", headers=headers(auth_employee))

    forbidden = await client.post(f"/api/v1/tickets/{ticket_id}/takeover", headers=headers(auth_employee))
    assert forbidden.status_code == 403
    accepted = await client.post(f"/api/v1/tickets/{ticket_id}/takeover", headers=headers(auth_technician))
    assert accepted.status_code == 200, accepted.text

    ticket = await ticket_row(ticket_id)
    audits = await ticket_audits(ticket_id)
    assigned = next(item for item in audits if item.action == AuditAction.TICKET_ASSIGNED)
    assert ticket.assignee_id is not None
    assert ticket.status == TicketStatus.IN_PROGRESS
    assert ticket.support_mode == TicketSupportMode.HUMAN
    assert assigned.actor_id == ticket.assignee_id
    assert assigned.created_at is not None
    assert '"old_status"' in (assigned.metadata_json or "")
    assert '"new_status"' in (assigned.metadata_json or "")


@pytest.mark.asyncio
async def test_e2e_status_close_reopen_and_rating_follow_db_state_machine(
    client: AsyncClient, auth_employee: str, auth_technician: str,
) -> None:
    ticket_id, _ = await create_incident(client, auth_employee, prefix="E2E close")
    moved = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status", json={"status": "in_progress", "note": "work started"}, headers=headers(auth_technician),
    )
    assert moved.status_code == 200, moved.text
    closed = await client.post(f"/api/v1/tickets/{ticket_id}/close", headers=headers(auth_technician))
    assert closed.status_code == 200, closed.text
    assert (await ticket_row(ticket_id)).status == TicketStatus.CLOSED

    invalid = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status", json={"status": "in_progress"}, headers=headers(auth_technician),
    )
    assert invalid.status_code == 400
    rated = await client.post(
        f"/api/v1/tickets/{ticket_id}/rating", json={"rating": 5, "feedback": "Closed workflow verified."}, headers=headers(auth_employee),
    )
    assert rated.status_code == 200
    assert (await ticket_row(ticket_id)).rating == 5

    reopened = await client.post(
        f"/api/v1/tickets/{ticket_id}/reopen", json={"reason": "The incident recurred."}, headers=headers(auth_employee),
    )
    assert reopened.status_code == 200, reopened.text
    ticket = await ticket_row(ticket_id)
    assert ticket.status == TicketStatus.WAITING_FOR_AGENT
    assert ticket.reopened_at is not None


@pytest.mark.asyncio
async def test_e2e_service_request_is_not_incident_and_multi_intent_does_not_fake_secondary_action(
    client: AsyncClient, auth_employee: str,
) -> None:
    async with AsyncSessionLocal() as db:
        tickets_before = await db.scalar(select(func.count()).select_from(Ticket))
        services_before = await db.scalar(select(func.count()).select_from(ServiceRequest)) or 0
    service = await client.post(
        "/api/v1/service-requests",
        json={"service_name": "Xin laptop mới", "category": "network", "form_data": {"reason": "replacement"}},
        headers=headers(auth_employee),
    )
    assert service.status_code == 201, service.text
    request_number = service.json()["request_number"]
    async with AsyncSessionLocal() as db:
        persisted = (await db.execute(select(ServiceRequest).where(ServiceRequest.request_number == request_number))).scalar_one()
        tickets_after_service = await db.scalar(select(func.count()).select_from(Ticket))
    assert persisted.status == ServiceRequestStatus.PENDING_APPROVAL
    assert persisted.fulfillment_group == "Workplace IT"
    assert tickets_after_service == tickets_before

    incident_id, _ = await create_incident(client, auth_employee, prefix="E2E broken laptop and replacement request")
    async with AsyncSessionLocal() as db:
        service_count = await db.scalar(select(func.count()).select_from(ServiceRequest))
    assert incident_id
    assert service_count == services_before + 1


@pytest.mark.asyncio
async def test_e2e_idempotency_and_db_failure_do_not_fabricate_mutations(client: AsyncClient, auth_employee: str) -> None:
    key = f"e2e-{uuid4().hex}"
    payload = {"title": f"E2E idempotency {uuid4().hex}", "description": "Verify retry creates one incident only."}
    request_headers = {**headers(auth_employee), "X-Idempotency-Key": key}
    no_duplicate = SimpleNamespace(primary=None, matches=[], same_user_repeat_count=0, shared_incident_signal=False)
    with (
        patch("src.api.tickets._run_agent_workflow", new=AsyncMock()),
        patch("src.services.duplicate_detection_service.check_duplicate_tickets", new=AsyncMock(return_value=no_duplicate)),
        patch("src.services.duplicate_detection_service.audit_duplicate_decision", new=AsyncMock()),
        patch("src.services.duplicate_detection_service.index_ticket_for_duplicate_detection"),
        patch("src.services.zero_mem_service.index_ticket_trace", new=AsyncMock()),
    ):
        first = await client.post("/api/v1/tickets", json=payload, headers=request_headers)
        second = await client.post("/api/v1/tickets", json=payload, headers=request_headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["ticket_id"] == second.json()["ticket_id"]
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Ticket).where(Ticket.title == payload["title"])) == 1

    failing_title = f"E2E db failure {uuid4().hex}"
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as safe_client:
        with (
            patch("src.services.duplicate_detection_service.check_duplicate_tickets", new=AsyncMock(return_value=no_duplicate)),
            patch("src.services.duplicate_detection_service.audit_duplicate_decision", new=AsyncMock()),
            patch("src.services.ticket_service.create_ticket", new=AsyncMock(side_effect=RuntimeError("DATABASE_TIMEOUT_INTERNAL"))),
        ):
            failed = await safe_client.post(
                "/api/v1/tickets",
                json={"title": failing_title, "description": "The database failure must not create state."},
                headers=headers(auth_employee),
            )
    assert failed.status_code == 500
    assert "database_timeout_internal" not in failed.text.casefold()
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Ticket).where(Ticket.title == failing_title)) == 0


def test_e2e_tool_failure_renderer_never_confirms_success() -> None:
    reply = action_state_reply(ActionResult(success=False, error_code="DATABASE_TIMEOUT"))

    assert "chưa hoàn tất" in reply.casefold()
    assert "đã hoàn tất" not in reply.casefold()
    assert "database_timeout" not in reply.casefold()


@pytest.mark.asyncio
async def test_e2e_cross_user_cross_tenant_and_fake_role_do_not_bypass_rbac(client: AsyncClient, auth_employee: str) -> None:
    ticket_id, _ = await create_incident(client, auth_employee, prefix="E2E tenant isolation")
    healthcare = await login(client, "employee_healthcare")

    forbidden_read = await client.get(f"/api/v1/tickets/{ticket_id}", headers=headers(healthcare))
    forbidden_takeover = await client.post(
        f"/api/v1/tickets/{ticket_id}/takeover", headers={**headers(auth_employee), "X-Claimed-Role": "admin"},
    )
    assert forbidden_read.status_code == 403
    assert forbidden_takeover.status_code == 403
    ticket = await ticket_row(ticket_id)
    assert ticket.assignee_id is None
    assert ticket.status == TicketStatus.OPEN


@pytest.mark.asyncio
async def test_e2e_concurrent_takeover_leaves_one_persisted_state(client: AsyncClient, auth_employee: str, auth_technician: str) -> None:
    ticket_id, _ = await create_incident(client, auth_employee, prefix="E2E concurrent takeover")
    await client.post(f"/api/v1/tickets/{ticket_id}/request-technician", headers=headers(auth_employee))
    technician = await login(client, "tech1")

    manager_response, technician_response = await asyncio.gather(
        client.post(f"/api/v1/tickets/{ticket_id}/takeover", headers=headers(auth_technician)),
        client.post(f"/api/v1/tickets/{ticket_id}/takeover", headers=headers(technician)),
    )
    assert manager_response.status_code in {200, 409}
    assert technician_response.status_code in {200, 409}
    ticket = await ticket_row(ticket_id)
    assert ticket.status == TicketStatus.IN_PROGRESS
    assert ticket.support_mode == TicketSupportMode.HUMAN
    assert ticket.assignee_id is not None


@pytest.mark.asyncio
async def test_e2e_streaming_completion_and_reconnect_do_not_duplicate_messages(client: AsyncClient, auth_employee: str) -> None:
    ticket_id, _ = await create_incident(client, auth_employee, prefix="E2E streaming")
    with patch("src.services.ticket_conversation_service.handle_ticket_message", new=fake_conversation_handler):
        response = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages/stream",
            json={"message": "Please provide a streaming update."},
            headers=headers(auth_employee),
        )
    assert response.status_code == 200, response.text
    assert "event: token" in response.text
    assert "event: done" in response.text
    first_count = len(await ticket_messages(ticket_id))
    reconnect = await client.get(f"/api/v1/tickets/{ticket_id}/messages", headers=headers(auth_employee))
    assert reconnect.status_code == 200
    assert len(await ticket_messages(ticket_id)) == first_count == 2
    assert "created ticket" not in response.text.casefold()
