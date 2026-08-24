"""HTTP E2E coverage for the approval-gated Service Request branch only."""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.audit_log import AuditAction, AuditLog
from src.models.service_request import ServiceRequestStatus
from src.models.user import CompanyUnit, UserRole
from src.services.auth_service import create_user


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client: AsyncClient, username: str, password: str = "demo123") -> str:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def create_request(client: AsyncClient, employee_token: str, *, approval_required: bool) -> dict:
    catalog = await client.get("/api/v1/service-requests/catalog", headers=headers(employee_token))
    item = next(row for row in catalog.json()["items"] if bool(row["approval_roles"]) is approval_required)
    response = await client.post(
        "/api/v1/service-requests",
        json={"service_name": item["service_name"], "category": "client-bypass-attempt", "form_data": {"purpose": "C2 approval E2E"}},
        headers=headers(employee_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def request_audits(request_id: int) -> list[AuditLog]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AuditLog).where(AuditLog.service_request_id == request_id).order_by(AuditLog.id))
        return list(result.scalars())


async def tenant_manager(client: AsyncClient, unit: CompanyUnit) -> str:
    username = f"c2-manager-{uuid4().hex[:12]}"
    async with AsyncSessionLocal() as db:
        await create_user(
            db, username=username, email=f"{username}@example.test", full_name="C2 Tenant Manager",
            password="demo123", role=UserRole.MANAGER, company_unit=unit, department="Operations",
        )
        await db.commit()
    return await login(client, username)


@pytest.mark.asyncio
async def test_sr_app_01_02_required_request_is_pending_and_absent_from_technician_queue(client: AsyncClient, auth_employee: str) -> None:
    request = await create_request(client, auth_employee, approval_required=True)
    assert request["status"] == ServiceRequestStatus.PENDING_APPROVAL.value
    tech = await login(client, "tech1")
    queue = await client.get("/api/v1/service-requests/technician/queue", headers=headers(tech))
    assert request["request_number"] not in {row["request_number"] for row in queue.json()["items"]}
    assert any(log.action == AuditAction.SERVICE_REQUEST_APPROVAL_REQUIRED for log in await request_audits(request["id"]))


@pytest.mark.asyncio
async def test_sr_app_03_04_05_manager_queue_and_non_approvers_denied(client: AsyncClient, auth_employee: str) -> None:
    request = await create_request(client, auth_employee, approval_required=True)
    manager = await login(client, "manager1")
    pending = await client.get("/api/v1/service-requests/pending-approval", headers=headers(manager))
    assert pending.status_code == 200
    assert request["request_number"] in {row["request_number"] for row in pending.json()["items"]}
    employee = await client.post(f"/api/v1/service-requests/{request['request_number']}/approve", json={}, headers=headers(auth_employee))
    technician = await client.post(f"/api/v1/service-requests/{request['request_number']}/approve", json={}, headers=headers(await login(client, "tech1")))
    assert employee.status_code == 403
    assert technician.status_code == 403


@pytest.mark.asyncio
async def test_sr_app_06_cross_tenant_manager_cannot_view_or_decide(client: AsyncClient, auth_employee: str) -> None:
    request = await create_request(client, auth_employee, approval_required=True)
    manager = await tenant_manager(client, CompanyUnit.HEALTHCARE)
    pending = await client.get("/api/v1/service-requests/pending-approval", headers=headers(manager))
    assert request["request_number"] not in {row["request_number"] for row in pending.json()["items"]}
    decision = await client.post(f"/api/v1/service-requests/{request['request_number']}/approve", json={}, headers=headers(manager))
    assert decision.status_code == 403


@pytest.mark.asyncio
async def test_sr_app_07_approval_persists_audits_and_enters_existing_queue(client: AsyncClient, auth_employee: str) -> None:
    request = await create_request(client, auth_employee, approval_required=True)
    manager = await login(client, "manager1")
    approved = await client.post(f"/api/v1/service-requests/{request['request_number']}/approve", json={"comment": "Business need confirmed"}, headers=headers(manager))
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == ServiceRequestStatus.SUBMITTED.value
    assert approved.json()["approved_at"] is not None
    tech = await login(client, "tech1")
    queue = await client.get("/api/v1/service-requests/technician/queue", headers=headers(tech))
    assert request["request_number"] in {row["request_number"] for row in queue.json()["items"]}
    takeover = await client.post(f"/api/v1/service-requests/{request['request_number']}/takeover", headers=headers(tech))
    assert takeover.status_code == 200
    started = await client.post(f"/api/v1/service-requests/{request['request_number']}/transition", json={"target_status": "in_progress"}, headers=headers(tech))
    assert started.status_code == 200
    fulfilled = await client.post(f"/api/v1/service-requests/{request['request_number']}/transition", json={"target_status": "fulfilled"}, headers=headers(tech))
    assert fulfilled.status_code == 200
    assert any(log.action == AuditAction.SERVICE_REQUEST_APPROVED for log in await request_audits(request["id"]))


@pytest.mark.asyncio
async def test_sr_app_08_12_rejection_is_terminal_audited_and_visible_to_employee(client: AsyncClient, auth_employee: str) -> None:
    request = await create_request(client, auth_employee, approval_required=True)
    manager = await login(client, "manager1")
    rejected = await client.post(f"/api/v1/service-requests/{request['request_number']}/reject", json={"reason": "Missing required business justification"}, headers=headers(manager))
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == ServiceRequestStatus.REJECTED.value
    assert rejected.json()["rejection_reason"] == "Missing required business justification"
    tech = await login(client, "tech1")
    queue = await client.get("/api/v1/service-requests/technician/queue", headers=headers(tech))
    assert request["request_number"] not in {row["request_number"] for row in queue.json()["items"]}
    employee_detail = await client.get(f"/api/v1/service-requests/{request['request_number']}", headers=headers(auth_employee))
    assert employee_detail.json()["status"] == ServiceRequestStatus.REJECTED.value
    assert employee_detail.json()["rejection_reason"] == "Missing required business justification"
    assert any(log.action == AuditAction.SERVICE_REQUEST_REJECTED for log in await request_audits(request["id"]))


@pytest.mark.asyncio
async def test_sr_app_09_double_approval_is_conflict(client: AsyncClient, auth_employee: str) -> None:
    request = await create_request(client, auth_employee, approval_required=True)
    manager = await login(client, "manager1")
    first = await client.post(f"/api/v1/service-requests/{request['request_number']}/approve", json={}, headers=headers(manager))
    second = await client.post(f"/api/v1/service-requests/{request['request_number']}/approve", json={}, headers=headers(manager))
    assert first.status_code == 200
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_sr_app_10_approve_reject_race_has_one_decision(client: AsyncClient, auth_employee: str) -> None:
    request = await create_request(client, auth_employee, approval_required=True)
    manager = await login(client, "manager1")
    admin = await login(client, "admin", "admin123")
    approved, rejected = await asyncio.gather(
        client.post(f"/api/v1/service-requests/{request['request_number']}/approve", json={}, headers=headers(manager)),
        client.post(f"/api/v1/service-requests/{request['request_number']}/reject", json={"reason": "Concurrent decision"}, headers=headers(admin)),
    )
    assert sorted([approved.status_code, rejected.status_code]) == [200, 409]
    actions = [log.action for log in await request_audits(request["id"])]
    assert len([action for action in actions if action in {AuditAction.SERVICE_REQUEST_APPROVED, AuditAction.SERVICE_REQUEST_REJECTED}]) == 1


@pytest.mark.asyncio
async def test_sr_app_11_direct_catalog_item_still_bypasses_approval(client: AsyncClient, auth_employee: str) -> None:
    request = await create_request(client, auth_employee, approval_required=False)
    assert request["status"] == ServiceRequestStatus.SUBMITTED.value
    tech = await login(client, "tech1")
    queue = await client.get("/api/v1/service-requests/technician/queue", headers=headers(tech))
    assert request["request_number"] in {row["request_number"] for row in queue.json()["items"]}
