"""Production-style HTTP E2E coverage for Service Request fulfillment."""
from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.audit_log import AuditAction, AuditLog
from src.models.service_request import ServiceRequest, ServiceRequestStatus
from src.models.user import CompanyUnit, UserRole
from src.services.auth_service import create_user


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client: AsyncClient, username: str, password: str = "demo123") -> str:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def create_submitted_request(client: AsyncClient, token: str) -> dict:
    catalog = await client.get("/api/v1/service-requests/catalog", headers=headers(token))
    assert catalog.status_code == 200, catalog.text
    item = next(row for row in catalog.json()["items"] if not row["approval_roles"])
    response = await client.post(
        "/api/v1/service-requests",
        json={"service_name": item["service_name"], "category": "client-controlled-but-ignored", "form_data": {"purpose": "E2E fulfillment"}},
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == ServiceRequestStatus.SUBMITTED.value
    return response.json()


async def audits_for(request_id: int) -> list[AuditLog]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AuditLog).where(AuditLog.service_request_id == request_id).order_by(AuditLog.id)
        )
        return list(result.scalars())


async def create_tenant_technician(client: AsyncClient, unit: CompanyUnit) -> str:
    username = f"sr-tech-{uuid4().hex[:12]}"
    async with AsyncSessionLocal() as db:
        await create_user(
            db, username=username, email=f"{username}@example.test", full_name="SR tenant technician",
            password="demo123", role=UserRole.TECHNICIAN, company_unit=unit, department="IT",
        )
        await db.commit()
    return await login(client, username)


@pytest.mark.asyncio
async def test_e2e_sr_01_employee_submission_persists(client: AsyncClient, auth_employee: str) -> None:
    created = await create_submitted_request(client, auth_employee)
    async with AsyncSessionLocal() as db:
        row = await db.get(ServiceRequest, created["id"])
        assert row is not None
        assert row.request_number == created["request_number"]
        assert row.status == ServiceRequestStatus.SUBMITTED


@pytest.mark.asyncio
async def test_e2e_sr_02_03_eligible_queue_takeover_persists_and_audits(client: AsyncClient, auth_employee: str) -> None:
    created = await create_submitted_request(client, auth_employee)
    tech = await login(client, "tech1")
    queue = await client.get("/api/v1/service-requests/technician/queue", headers=headers(tech))
    assert queue.status_code == 200, queue.text
    assert created["request_number"] in {item["request_number"] for item in queue.json()["items"]}
    taken = await client.post(f"/api/v1/service-requests/{created['request_number']}/takeover", headers=headers(tech))
    assert taken.status_code == 200, taken.text
    assert taken.json()["status"] == ServiceRequestStatus.ASSIGNED.value
    assert taken.json()["assignee_name"]
    assigned_audit = next(log for log in await audits_for(created["id"]) if log.action == AuditAction.SERVICE_REQUEST_ASSIGNED)
    assert json.loads(assigned_audit.metadata_json or "{}") == {
        "request_number": created["request_number"], "tenant": CompanyUnit.REAL_ESTATE.value,
        "old_status": "submitted", "new_status": "assigned",
    }


@pytest.mark.asyncio
async def test_e2e_sr_04_employee_cannot_fulfill(client: AsyncClient, auth_employee: str) -> None:
    created = await create_submitted_request(client, auth_employee)
    response = await client.post(f"/api/v1/service-requests/{created['request_number']}/takeover", headers=headers(auth_employee))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_e2e_sr_05_cross_tenant_technician_cannot_view_or_mutate(client: AsyncClient, auth_employee: str) -> None:
    created = await create_submitted_request(client, auth_employee)
    other_tenant_tech = await create_tenant_technician(client, CompanyUnit.HEALTHCARE)
    detail = await client.get(f"/api/v1/service-requests/{created['request_number']}", headers=headers(other_tenant_tech))
    takeover = await client.post(f"/api/v1/service-requests/{created['request_number']}/takeover", headers=headers(other_tenant_tech))
    assert detail.status_code == 403
    assert takeover.status_code == 403


@pytest.mark.asyncio
async def test_e2e_sr_06_07_valid_and_invalid_transition(client: AsyncClient, auth_employee: str) -> None:
    created = await create_submitted_request(client, auth_employee)
    tech = await login(client, "tech1")
    await client.post(f"/api/v1/service-requests/{created['request_number']}/takeover", headers=headers(tech))
    invalid = await client.post(
        f"/api/v1/service-requests/{created['request_number']}/transition",
        json={"target_status": "fulfilled"}, headers=headers(tech),
    )
    assert invalid.status_code == 409
    started = await client.post(
        f"/api/v1/service-requests/{created['request_number']}/transition",
        json={"target_status": "in_progress"}, headers=headers(tech),
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == ServiceRequestStatus.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_e2e_sr_08_no_task_model_is_advertised_as_persisted_work(client: AsyncClient, auth_employee: str) -> None:
    """Catalog has no task/checklist definition, so this batch adds no fake task endpoint."""
    created = await create_submitted_request(client, auth_employee)
    response = await client.post(f"/api/v1/service-requests/{created['request_number']}/tasks", headers=headers(auth_employee))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_e2e_sr_09_10_completion_audit_and_employee_visibility(client: AsyncClient, auth_employee: str) -> None:
    created = await create_submitted_request(client, auth_employee)
    tech = await login(client, "tech1")
    await client.post(f"/api/v1/service-requests/{created['request_number']}/takeover", headers=headers(tech))
    await client.post(f"/api/v1/service-requests/{created['request_number']}/transition", json={"target_status": "in_progress"}, headers=headers(tech))
    complete = await client.post(f"/api/v1/service-requests/{created['request_number']}/transition", json={"target_status": "fulfilled"}, headers=headers(tech))
    assert complete.status_code == 200, complete.text
    assert complete.json()["fulfilled_at"] is not None
    retry = await client.post(f"/api/v1/service-requests/{created['request_number']}/transition", json={"target_status": "fulfilled"}, headers=headers(tech))
    assert retry.status_code == 200
    mine = await client.get("/api/v1/service-requests/mine", headers=headers(auth_employee))
    employee_item = next(row for row in mine.json()["items"] if row["id"] == created["id"])
    assert employee_item["status"] == ServiceRequestStatus.FULFILLED.value
    fulfilled_audits = [log for log in await audits_for(created["id"]) if log.action == AuditAction.SERVICE_REQUEST_FULFILLED]
    assert len(fulfilled_audits) == 1


@pytest.mark.asyncio
async def test_e2e_sr_11_concurrent_takeover_has_one_winner(client: AsyncClient, auth_employee: str) -> None:
    created = await create_submitted_request(client, auth_employee)
    tech = await login(client, "tech1")
    admin = await login(client, "admin", "admin123")
    first, second = await asyncio.gather(
        client.post(f"/api/v1/service-requests/{created['request_number']}/takeover", headers=headers(tech)),
        client.post(f"/api/v1/service-requests/{created['request_number']}/takeover", headers=headers(admin)),
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    async with AsyncSessionLocal() as db:
        row = await db.get(ServiceRequest, created["id"])
        assert row is not None and row.assignee_id is not None and row.status == ServiceRequestStatus.ASSIGNED
    assert len([log for log in await audits_for(created["id"]) if log.action == AuditAction.SERVICE_REQUEST_ASSIGNED]) == 1


@pytest.mark.asyncio
async def test_e2e_sr_12_failed_mutation_has_no_fake_success_or_state_change(client: AsyncClient, auth_employee: str) -> None:
    created = await create_submitted_request(client, auth_employee)
    tech = await login(client, "tech1")
    failure = await client.post(
        f"/api/v1/service-requests/{created['request_number']}/transition",
        json={"target_status": "in_progress"}, headers=headers(tech),
    )
    assert failure.status_code == 409
    detail = await client.get(f"/api/v1/service-requests/{created['request_number']}", headers=headers(auth_employee))
    assert detail.status_code == 200
    assert detail.json()["status"] == ServiceRequestStatus.SUBMITTED.value
