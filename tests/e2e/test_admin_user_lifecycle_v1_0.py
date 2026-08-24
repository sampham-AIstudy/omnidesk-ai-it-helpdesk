"""Focused HTTP + persistence coverage for C1 admin user lifecycle hardening."""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.audit_log import AuditAction, AuditLog


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client: AsyncClient, username: str, password: str = "demo123") -> str:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def create_managed_user(client: AsyncClient, admin_token: str, *, role: str = "employee", unit: str = "real_estate") -> dict:
    suffix = uuid4().hex[:12]
    response = await client.post(
        "/api/v1/admin/users",
        json={
            "username": f"c1-user-{suffix}", "email": f"c1-user-{suffix}@example.test",
            "full_name": "C1 Managed User", "password": "secure-password", "role": role,
            "company_unit": unit, "department": "Operations",
        }, headers=headers(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def user_audits(target_user_id: int) -> list[AuditLog]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AuditLog).order_by(AuditLog.id.desc()))
        return [
            log for log in result.scalars()
            if f'"target_user_id": {target_user_id}' in (log.metadata_json or "")
        ]


@pytest.mark.asyncio
async def test_admin_update_is_typed_persisted_and_audited(client: AsyncClient, auth_admin: str) -> None:
    user = await create_managed_user(client, auth_admin)
    response = await client.patch(
        f"/api/v1/admin/users/{user['id']}",
        json={"full_name": "Updated C1 User", "department": "Security", "company_unit": "healthcare", "is_vip": True},
        headers=headers(auth_admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["full_name"] == "Updated C1 User"
    assert response.json()["company_unit"] == "healthcare"
    audit = next(log for log in await user_audits(user["id"]) if log.action == AuditAction.USER_UPDATED)
    assert "password" not in (audit.metadata_json or "").lower()
    assert "department" in (audit.metadata_json or "")


@pytest.mark.asyncio
async def test_non_admin_roles_cannot_mutate_users(client: AsyncClient, auth_admin: str, auth_employee: str) -> None:
    user = await create_managed_user(client, auth_admin)
    tokens = [auth_employee, await login(client, "tech1"), await login(client, "manager1")]
    for token in tokens:
        response = await client.patch(f"/api/v1/admin/users/{user['id']}", json={"department": "Denied"}, headers=headers(token))
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_enum_and_mass_assignment_are_rejected(client: AsyncClient, auth_admin: str) -> None:
    user = await create_managed_user(client, auth_admin)
    for payload in ({"role": "root"}, {"company_unit": "elsewhere"}, {"hashed_password": "not-allowed"}):
        response = await client.patch(f"/api/v1/admin/users/{user['id']}", json=payload, headers=headers(auth_admin))
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_email_is_rejected(client: AsyncClient, auth_admin: str) -> None:
    first = await create_managed_user(client, auth_admin)
    second = await create_managed_user(client, auth_admin)
    response = await client.patch(f"/api/v1/admin/users/{second['id']}", json={"email": first["email"]}, headers=headers(auth_admin))
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_deactivate_reactivate_and_audit(client: AsyncClient, auth_admin: str) -> None:
    user = await create_managed_user(client, auth_admin)
    deactivate = await client.patch(f"/api/v1/admin/users/{user['id']}", json={"is_active": False}, headers=headers(auth_admin))
    assert deactivate.status_code == 200 and deactivate.json()["is_active"] is False
    reactivate = await client.patch(f"/api/v1/admin/users/{user['id']}", json={"is_active": True}, headers=headers(auth_admin))
    assert reactivate.status_code == 200 and reactivate.json()["is_active"] is True
    actions = {log.action for log in await user_audits(user["id"])}
    assert {AuditAction.USER_CREATED, AuditAction.USER_DEACTIVATED, AuditAction.USER_REACTIVATED} <= actions


@pytest.mark.asyncio
async def test_self_deactivation_is_rejected(client: AsyncClient, auth_admin: str) -> None:
    me = await client.get("/api/v1/auth/me", headers=headers(auth_admin))
    response = await client.patch(f"/api/v1/admin/users/{me.json()['id']}", json={"is_active": False}, headers=headers(auth_admin))
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_e2e_admin_deactivation_revokes_old_token_and_reactivation_restores_access(client: AsyncClient, auth_admin: str) -> None:
    user = await create_managed_user(client, auth_admin, unit="automotive")
    old_token = await login(client, user["username"], "secure-password")
    assert (await client.get("/api/v1/auth/me", headers=headers(old_token))).status_code == 200
    deactivate = await client.patch(f"/api/v1/admin/users/{user['id']}", json={"is_active": False}, headers=headers(auth_admin))
    assert deactivate.status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=headers(old_token))).status_code == 401
    inactive_login = await client.post("/api/v1/auth/login", json={"username": user["username"], "password": "secure-password"})
    assert inactive_login.status_code == 401
    reactivate = await client.patch(f"/api/v1/admin/users/{user['id']}", json={"is_active": True}, headers=headers(auth_admin))
    assert reactivate.status_code == 200
    new_token = await login(client, user["username"], "secure-password")
    assert (await client.get("/api/v1/auth/me", headers=headers(new_token))).status_code == 200
    assert any(log.action == AuditAction.USER_DEACTIVATED for log in await user_audits(user["id"]))
