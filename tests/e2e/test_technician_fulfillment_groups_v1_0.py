"""HTTP + SQLite coverage for C3 technician fulfillment-group eligibility."""
from __future__ import annotations

import json
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.audit_log import AuditAction, AuditLog

HARDWARE_GROUP = "Workplace IT"
NETWORK_GROUP = "Network Operations"


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client: AsyncClient, username: str, password: str = "demo123") -> str:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def create_user(client: AsyncClient, admin: str, *, role: str, unit: str = "real_estate") -> dict:
    suffix = uuid4().hex[:12]
    response = await client.post(
        "/api/v1/admin/users",
        json={
            "username": f"c3-{role}-{suffix}", "email": f"c3-{role}-{suffix}@example.test",
            "full_name": "C3 Test User", "password": "secure-password", "role": role,
            "company_unit": unit, "department": "IT",
        },
        headers=headers(admin),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def set_groups(client: AsyncClient, admin: str, technician_id: int, groups: list[str]) -> dict:
    response = await client.put(
        f"/api/v1/admin/technicians/{technician_id}/fulfillment-groups",
        json={"fulfillment_groups": groups}, headers=headers(admin),
    )
    assert response.status_code == 200, response.text
    return response.json()


async def create_direct_request(client: AsyncClient, token: str, group: str) -> dict:
    catalog = await client.get("/api/v1/service-requests/catalog", headers=headers(token))
    assert catalog.status_code == 200, catalog.text
    item = next(row for row in catalog.json()["items"] if row["fulfillment_group"] == group and not row["approval_roles"])
    response = await client.post(
        "/api/v1/service-requests",
        json={"service_name": item["service_name"], "category": "untrusted-client-category", "form_data": {"purpose": "C3 E2E"}},
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["fulfillment_group"] == group
    assert response.json()["status"] == "submitted"
    return response.json()


async def group_audits(technician_id: int) -> list[AuditLog]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AuditLog).where(AuditLog.action == AuditAction.TECHNICIAN_FULFILLMENT_GROUPS_UPDATED))
        return [
            row for row in result.scalars()
            if json.loads(row.metadata_json or "{}").get("target_user_id") == technician_id
        ]


@pytest.mark.asyncio
async def test_fg_01_02_admin_assigns_one_and_multiple_canonical_groups(client: AsyncClient, auth_admin: str) -> None:
    technician = await create_user(client, auth_admin, role="technician")
    allowed = await client.get("/api/v1/admin/fulfillment-groups", headers=headers(auth_admin))
    assert allowed.status_code == 200
    assert {HARDWARE_GROUP, NETWORK_GROUP} <= set(allowed.json()["items"])
    one = await set_groups(client, auth_admin, technician["id"], [HARDWARE_GROUP])
    assert one["fulfillment_groups"] == [HARDWARE_GROUP]
    many = await set_groups(client, auth_admin, technician["id"], [NETWORK_GROUP, HARDWARE_GROUP])
    assert many["fulfillment_groups"] == [NETWORK_GROUP, HARDWARE_GROUP]
    assert any(log.action == AuditAction.TECHNICIAN_FULFILLMENT_GROUPS_UPDATED for log in await group_audits(technician["id"]))


@pytest.mark.asyncio
async def test_fg_03_04_05_admin_only_and_validated_targets(client: AsyncClient, auth_admin: str, auth_employee: str) -> None:
    technician = await create_user(client, auth_admin, role="technician")
    denied = await client.put(
        f"/api/v1/admin/technicians/{technician['id']}/fulfillment-groups",
        json={"fulfillment_groups": [HARDWARE_GROUP]}, headers=headers(auth_employee),
    )
    assert denied.status_code == 403
    unknown = await client.put(
        f"/api/v1/admin/technicians/{technician['id']}/fulfillment-groups",
        json={"fulfillment_groups": ["Not A Canonical Group"]}, headers=headers(auth_admin),
    )
    assert unknown.status_code == 422
    employee = await create_user(client, auth_admin, role="employee")
    invalid_target = await client.put(
        f"/api/v1/admin/technicians/{employee['id']}/fulfillment-groups",
        json={"fulfillment_groups": [HARDWARE_GROUP]}, headers=headers(auth_admin),
    )
    assert invalid_target.status_code == 422


@pytest.mark.asyncio
async def test_fg_06_to_10_queue_visibility_takeover_and_tenant_intersection(client: AsyncClient, auth_admin: str, auth_employee: str) -> None:
    technician = await create_user(client, auth_admin, role="technician")
    tech_token = await login(client, technician["username"], "secure-password")
    hardware = await create_direct_request(client, auth_employee, HARDWARE_GROUP)
    network = await create_direct_request(client, auth_employee, NETWORK_GROUP)
    empty = await client.get("/api/v1/service-requests/technician/queue", headers=headers(tech_token))
    assert empty.status_code == 200 and empty.json()["items"] == []
    await set_groups(client, auth_admin, technician["id"], [HARDWARE_GROUP])
    queue = await client.get("/api/v1/service-requests/technician/queue", headers=headers(tech_token))
    numbers = {item["request_number"] for item in queue.json()["items"]}
    assert hardware["request_number"] in numbers
    assert network["request_number"] not in numbers
    assert (await client.post(f"/api/v1/service-requests/{hardware['request_number']}/takeover", headers=headers(tech_token))).status_code == 200
    assert (await client.post(f"/api/v1/service-requests/{network['request_number']}/takeover", headers=headers(tech_token))).status_code == 403
    healthcare_employee = await create_user(client, auth_admin, role="employee", unit="healthcare")
    healthcare_token = await login(client, healthcare_employee["username"], "secure-password")
    other_tenant = await create_direct_request(client, healthcare_token, HARDWARE_GROUP)
    assert (await client.post(f"/api/v1/service-requests/{other_tenant['request_number']}/takeover", headers=headers(tech_token))).status_code == 403


@pytest.mark.asyncio
async def test_fg_11_12_removal_blocks_new_work_but_keeps_owned_work(client: AsyncClient, auth_admin: str, auth_employee: str) -> None:
    technician = await create_user(client, auth_admin, role="technician")
    token = await login(client, technician["username"], "secure-password")
    await set_groups(client, auth_admin, technician["id"], [HARDWARE_GROUP])
    owned = await create_direct_request(client, auth_employee, HARDWARE_GROUP)
    assert (await client.post(f"/api/v1/service-requests/{owned['request_number']}/takeover", headers=headers(token))).status_code == 200
    await set_groups(client, auth_admin, technician["id"], [])
    started = await client.post(
        f"/api/v1/service-requests/{owned['request_number']}/transition",
        json={"target_status": "in_progress"}, headers=headers(token),
    )
    assert started.status_code == 200
    new_request = await create_direct_request(client, auth_employee, HARDWARE_GROUP)
    assert (await client.post(f"/api/v1/service-requests/{new_request['request_number']}/takeover", headers=headers(token))).status_code == 403


@pytest.mark.asyncio
async def test_fg_13_role_change_clears_memberships_and_removes_technician_access(client: AsyncClient, auth_admin: str) -> None:
    technician = await create_user(client, auth_admin, role="technician")
    token = await login(client, technician["username"], "secure-password")
    await set_groups(client, auth_admin, technician["id"], [HARDWARE_GROUP])
    changed = await client.patch(f"/api/v1/admin/users/{technician['id']}", json={"role": "employee"}, headers=headers(auth_admin))
    assert changed.status_code == 200
    assert (await client.get("/api/v1/service-requests/technician/queue", headers=headers(token))).status_code == 403
    await client.patch(f"/api/v1/admin/users/{technician['id']}", json={"role": "technician"}, headers=headers(auth_admin))
    groups = await client.get(f"/api/v1/admin/technicians/{technician['id']}/fulfillment-groups", headers=headers(auth_admin))
    assert groups.status_code == 200 and groups.json()["fulfillment_groups"] == []


@pytest.mark.asyncio
async def test_e2e_c3_admin_membership_controls_real_fulfillment_visibility(client: AsyncClient, auth_admin: str, auth_employee: str) -> None:
    technician = await create_user(client, auth_admin, role="technician")
    token = await login(client, technician["username"], "secure-password")
    await set_groups(client, auth_admin, technician["id"], [HARDWARE_GROUP])
    hardware = await create_direct_request(client, auth_employee, HARDWARE_GROUP)
    network = await create_direct_request(client, auth_employee, NETWORK_GROUP)
    queue = await client.get("/api/v1/service-requests/technician/queue", headers=headers(token))
    assert hardware["request_number"] in {row["request_number"] for row in queue.json()["items"]}
    assert network["request_number"] not in {row["request_number"] for row in queue.json()["items"]}
    assert (await client.post(f"/api/v1/service-requests/{hardware['request_number']}/takeover", headers=headers(token))).status_code == 200
    assert (await client.post(f"/api/v1/service-requests/{network['request_number']}/takeover", headers=headers(token))).status_code == 403
    await set_groups(client, auth_admin, technician["id"], [HARDWARE_GROUP, NETWORK_GROUP])
    refreshed = await client.get("/api/v1/service-requests/technician/queue", headers=headers(token))
    assert network["request_number"] in {row["request_number"] for row in refreshed.json()["items"]}
    assert (await client.post(f"/api/v1/service-requests/{network['request_number']}/takeover", headers=headers(token))).status_code == 200
