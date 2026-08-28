"""Admin-only HTTP contracts for governed policy lifecycle management."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.auth import get_current_user
from src.database import Base, get_db
from src.main import app
from src.models.user import CompanyUnit, User, UserRole
from src.services.auth_service import hash_password


@pytest_asyncio.fixture
async def api_client(tmp_path):
    """Local API database; avoids the session-wide RAG fixture and production data."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'policy-api.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        for username, role, password in (("employee", UserRole.EMPLOYEE, "demo123"), ("tech", UserRole.TECHNICIAN, "demo123"), ("manager", UserRole.MANAGER, "demo123"), ("admin", UserRole.ADMIN, "admin123")):
            session.add(User(username=username, email=f"{username}@example.test", full_name=username, hashed_password=hash_password(password), role=role, company_unit=CompanyUnit.CORPORATE))
        await session.commit()

    async def local_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = local_db
    app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


def rule_definition(*, allow_exception: bool = False) -> dict:
    return {
        "schema_version": 1,
        "default_effect": "advisory",
        "rules": [{
            "rule_id": "deny-endpoint", "effect": "deny", "action": ["disable_endpoint_protection"],
            "resource": {"type": "managed_endpoint"}, "subjects": {"roles": ["employee"]},
            "conditions": {"all": []}, "reason_code": "DENY_ENDPOINT", "user_message_template": "Denied.",
            "allow_exception": allow_exception,
        }],
    }


def version_payload(*, allow_exception: bool = False) -> dict:
    now = datetime.now(UTC) - timedelta(minutes=1)
    return {
        "title": "Endpoint protection", "content": "Do not disable endpoint protection.",
        "rule_definition": rule_definition(allow_exception=allow_exception), "priority": 100,
        "effective_from": now.isoformat(), "effective_until": None,
        "scopes": [{"tenant_id": "automotive", "resource_type": "managed_endpoint"}],
    }


async def login(client, username: str, password: str = "demo123") -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_policy_admin_rbac_all_management_routes(api_client):
    admin = await login(api_client, "admin", "admin123")
    employee = await login(api_client, "employee")
    manager = await login(api_client, "manager")
    technician = await login(api_client, "tech")
    payload = {"policy_key": "RBAC-POLICY", "tenant_id": "automotive", "global_policy": False, "name": "RBAC", "category": "security"}
    mutations = [
        ("post", "/api/v1/admin/policies", payload),
        ("patch", "/api/v1/admin/policies/missing", {"name": "Blocked"}),
        ("post", "/api/v1/admin/policies/missing/versions", version_payload()),
        ("post", "/api/v1/admin/policies/missing/versions/1/approve", None),
        ("post", "/api/v1/admin/policies/missing/versions/1/activate", None),
        ("post", "/api/v1/admin/policies/missing/deactivate", None),
        ("post", "/api/v1/admin/policies/missing/exceptions", {"subject_type": "user", "subject_id": "1", "reason": "Blocked", "valid_from": datetime.now(UTC).isoformat(), "valid_until": (datetime.now(UTC) + timedelta(days=1)).isoformat()}),
        ("post", "/api/v1/admin/policies/missing/exceptions/missing/approve", None),
        ("post", "/api/v1/admin/policies/missing/exceptions/missing/reject", None),
        ("post", "/api/v1/admin/policies/missing/exceptions/missing/revoke", None),
    ]
    reads = ["/api/v1/admin/policies", "/api/v1/admin/policies/missing", "/api/v1/admin/policies/missing/versions", "/api/v1/admin/policies/missing/versions/1", "/api/v1/admin/policies/missing/exceptions", "/api/v1/admin/policies/missing/audit"]
    for headers in (employee, technician, manager):
        for method, path, body in mutations:
            response = await getattr(api_client, method)(path, json=body, headers=headers)
            assert response.status_code == 403
        for path in reads:
            assert (await api_client.get(path, headers=headers)).status_code == 403
    assert (await api_client.post("/api/v1/admin/policies", json=payload, headers=admin)).status_code == 201


@pytest.mark.asyncio
async def test_policy_admin_lifecycle_e2e_and_audit(api_client):
    headers = await login(api_client, "admin", "admin123")
    policy = (await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-API-LIFECYCLE", "tenant_id": "automotive", "global_policy": False, "name": "Endpoint policy", "category": "security", "description": "Management API test"}, headers=headers)).json()
    policy_id = policy["id"]
    first = await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions", json=version_payload(allow_exception=True), headers=headers)
    assert first.status_code == 201 and first.json()["status"] == "draft"
    assert (await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions/1/approve", headers=headers)).status_code == 200
    assert (await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions/1/activate", headers=headers)).status_code == 200
    detail = await api_client.get(f"/api/v1/admin/policies/{policy_id}", headers=headers)
    assert detail.status_code == 200 and detail.json()["current_version"]["version_number"] == 1
    second = await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions", json=version_payload(allow_exception=True), headers=headers)
    assert second.status_code == 201
    assert (await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions/2/approve", headers=headers)).status_code == 200
    assert (await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions/2/activate", headers=headers)).status_code == 200
    versions = (await api_client.get(f"/api/v1/admin/policies/{policy_id}/versions", headers=headers)).json()
    assert [(item["version_number"], item["status"]) for item in versions] == [(2, "active"), (1, "superseded")]
    now = datetime.now(UTC)
    exception = await api_client.post(f"/api/v1/admin/policies/{policy_id}/exceptions", json={"subject_type": "user", "subject_id": "1", "action_type": "disable_endpoint_protection", "resource_type": "managed_endpoint", "reason": "Temporary maintenance", "valid_from": now.isoformat(), "valid_until": (now + timedelta(days=1)).isoformat()}, headers=headers)
    assert exception.status_code == 201
    exception_id = exception.json()["id"]
    assert (await api_client.post(f"/api/v1/admin/policies/{policy_id}/exceptions/{exception_id}/approve", headers=headers)).status_code == 200
    assert (await api_client.post(f"/api/v1/admin/policies/{policy_id}/exceptions/{exception_id}/revoke", headers=headers)).status_code == 200
    audit = (await api_client.get(f"/api/v1/admin/policies/{policy_id}/audit", headers=headers)).json()
    event_types = [item["event_type"] for item in audit["items"]]
    assert {"POLICY_ACTIVATED", "POLICY_SUPERSEDED", "POLICY_EXCEPTION_CREATED", "POLICY_EXCEPTION_APPROVED", "POLICY_EXCEPTION_REVOKED"} <= set(event_types)
    assert all("content" not in str(item["after_snapshot"]) for item in audit["items"])


@pytest.mark.asyncio
async def test_policy_admin_validation_pagination_and_parent_child_safety(api_client):
    headers = await login(api_client, "admin", "admin123")
    created = await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-API-SAFETY", "tenant_id": "automotive", "global_policy": False, "name": "Safety", "category": "security", "status": "active"}, headers=headers)
    assert created.status_code == 422
    policy = (await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-API-SAFETY", "tenant_id": "automotive", "global_policy": False, "name": "Safety", "category": "security"}, headers=headers)).json()
    policy_id = policy["id"]
    invalid = await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions", json={**version_payload(), "rule_definition": {"bad": True}}, headers=headers)
    assert invalid.status_code == 400
    invalid_window_payload = version_payload()
    invalid_window_payload["effective_until"] = invalid_window_payload["effective_from"]
    invalid_window = await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions", json=invalid_window_payload, headers=headers)
    assert invalid_window.status_code == 400
    assert (await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions", json={**version_payload(), "scopes": [{"tenant_id": "healthcare"}]}, headers=headers)).status_code == 404
    assert (await api_client.post(f"/api/v1/admin/policies/{policy_id}/versions", json={**version_payload(), "status": "active", "content_hash": "forbidden"}, headers=headers)).status_code == 422
    assert (await api_client.get("/api/v1/admin/policies?page=0", headers=headers)).status_code == 422
    assert (await api_client.get("/api/v1/admin/policies?page_size=101", headers=headers)).status_code == 422
    assert (await api_client.get("/api/v1/admin/policies?category=missing", headers=headers)).json()["items"] == []
    other = (await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-API-OTHER", "tenant_id": "healthcare", "global_policy": False, "name": "Other", "category": "security"}, headers=headers)).json()
    assert (await api_client.get(f"/api/v1/admin/policies/{other['id']}/versions/1", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_policy_list_detail_patch_and_schema_hardening(api_client):
    headers = await login(api_client, "admin", "admin123")
    for key, tenant, category in (("POL-LIST-1", "automotive", "security"), ("POL-LIST-2", "healthcare", "privacy")):
        response = await api_client.post("/api/v1/admin/policies", json={"policy_key": key, "tenant_id": tenant, "global_policy": False, "name": key, "category": category}, headers=headers)
        assert response.status_code == 201
    global_policy = await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-GLOBAL", "tenant_id": None, "global_policy": True, "name": "Global", "category": "security"}, headers=headers)
    assert global_policy.status_code == 201 and global_policy.json()["tenant_id"] is None
    assert (await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-BAD-GLOBAL", "name": "Bad", "category": "security"}, headers=headers)).status_code == 400
    assert (await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-LIST-1", "tenant_id": "automotive", "global_policy": False, "name": "Duplicate", "category": "security"}, headers=headers)).status_code == 409
    page = (await api_client.get("/api/v1/admin/policies?page=1&page_size=1&query=LIST&tenant=automotive&category=security&status=draft", headers=headers)).json()
    assert page["total"] == 1 and page["page_size"] == 1 and "description" not in page["items"][0]
    policy_id = page["items"][0]["id"]
    assert (await api_client.get("/api/v1/admin/policies/missing", headers=headers)).status_code == 404
    assert (await api_client.patch(f"/api/v1/admin/policies/{policy_id}", json={"name": "Renamed"}, headers=headers)).json()["name"] == "Renamed"
    for forbidden in ("policy_key", "tenant_id", "current_version_id", "status", "created_by", "approved_by", "audit_metadata"):
        assert (await api_client.patch(f"/api/v1/admin/policies/{policy_id}", json={forbidden: "blocked"}, headers=headers)).status_code == 422
    assert (await api_client.patch(f"/api/v1/admin/policies/{policy_id}", json={}, headers=headers)).status_code == 400
    detail = (await api_client.get(f"/api/v1/admin/policies/{policy_id}", headers=headers)).json()
    assert detail["version_count"] == 0 and detail["exception_count"] == 0 and "audit" not in detail


@pytest.mark.asyncio
async def test_version_transitions_deactivate_and_parent_child_isolation(api_client):
    headers = await login(api_client, "admin", "admin123")
    first = (await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-VERSION-A", "tenant_id": "automotive", "global_policy": False, "name": "A", "category": "security"}, headers=headers)).json()
    second = (await api_client.post("/api/v1/admin/policies", json={"policy_key": "POL-VERSION-B", "tenant_id": "automotive", "global_policy": False, "name": "B", "category": "security"}, headers=headers)).json()
    for policy in (first, second):
        assert (await api_client.post(f"/api/v1/admin/policies/{policy['id']}/versions", json=version_payload(), headers=headers)).status_code == 201
    assert (await api_client.get(f"/api/v1/admin/policies/{first['id']}/versions/1", headers=headers)).status_code == 200
    assert (await api_client.get(f"/api/v1/admin/policies/{first['id']}/versions/2", headers=headers)).status_code == 404
    assert (await api_client.post(f"/api/v1/admin/policies/{first['id']}/versions/1/activate", headers=headers)).status_code == 409
    assert (await api_client.post(f"/api/v1/admin/policies/{first['id']}/versions/1/approve", headers=headers)).status_code == 200
    assert (await api_client.post(f"/api/v1/admin/policies/{first['id']}/versions/1/approve", headers=headers)).status_code == 409
    assert (await api_client.post(f"/api/v1/admin/policies/{first['id']}/versions/1/activate", headers=headers)).status_code == 200
    assert (await api_client.post(f"/api/v1/admin/policies/{first['id']}/versions/1/activate", headers=headers)).status_code == 409
    assert (await api_client.post(f"/api/v1/admin/policies/{first['id']}/deactivate", headers=headers)).status_code == 200
    assert (await api_client.post(f"/api/v1/admin/policies/{first['id']}/deactivate", headers=headers)).status_code == 409
    assert (await api_client.get(f"/api/v1/admin/policies/{second['id']}/versions/1", headers=headers)).status_code == 200
    for key, mode in (("POL-FUTURE", "future"), ("POL-EXPIRED", "expired")):
        policy = (await api_client.post("/api/v1/admin/policies", json={"policy_key": key, "tenant_id": "automotive", "global_policy": False, "name": key, "category": "security"}, headers=headers)).json()
        payload = version_payload()
        if mode == "future":
            payload["effective_from"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        else:
            payload["effective_from"] = (datetime.now(UTC) - timedelta(days=2)).isoformat()
            payload["effective_until"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        assert (await api_client.post(f"/api/v1/admin/policies/{policy['id']}/versions", json=payload, headers=headers)).status_code == 201
        assert (await api_client.post(f"/api/v1/admin/policies/{policy['id']}/versions/1/approve", headers=headers)).status_code == 200
        assert (await api_client.post(f"/api/v1/admin/policies/{policy['id']}/versions/1/activate", headers=headers)).status_code == 400


@pytest.mark.asyncio
async def test_exception_lists_transitions_audit_and_cross_parent_hiding(api_client):
    headers = await login(api_client, "admin", "admin123")
    policies = []
    for key in ("POL-EXCEPTION-A", "POL-EXCEPTION-B"):
        policy = (await api_client.post("/api/v1/admin/policies", json={"policy_key": key, "tenant_id": "automotive", "global_policy": False, "name": key, "category": "security"}, headers=headers)).json()
        await api_client.post(f"/api/v1/admin/policies/{policy['id']}/versions", json=version_payload(allow_exception=True), headers=headers)
        await api_client.post(f"/api/v1/admin/policies/{policy['id']}/versions/1/approve", headers=headers)
        await api_client.post(f"/api/v1/admin/policies/{policy['id']}/versions/1/activate", headers=headers)
        policies.append(policy)
    now = datetime.now(UTC)
    payload = {"subject_type": "user", "subject_id": "1", "action_type": "disable_endpoint_protection", "reason": "Temporary", "valid_from": now.isoformat(), "valid_until": (now + timedelta(days=1)).isoformat()}
    created = await api_client.post(f"/api/v1/admin/policies/{policies[0]['id']}/exceptions", json=payload, headers=headers)
    assert created.status_code == 201 and created.json()["status"] == "pending"
    exception_id = created.json()["id"]
    assert (await api_client.get(f"/api/v1/admin/policies/{policies[0]['id']}/exceptions?page=1&page_size=1&status=pending", headers=headers)).json()["total"] == 1
    assert (await api_client.post(f"/api/v1/admin/policies/{policies[1]['id']}/exceptions/{exception_id}/approve", headers=headers)).status_code == 404
    assert (await api_client.post(f"/api/v1/admin/policies/{policies[0]['id']}/exceptions/{exception_id}/revoke", headers=headers)).status_code == 409
    assert (await api_client.post(f"/api/v1/admin/policies/{policies[0]['id']}/exceptions/{exception_id}/approve", headers=headers)).status_code == 200
    assert (await api_client.post(f"/api/v1/admin/policies/{policies[0]['id']}/exceptions/{exception_id}/approve", headers=headers)).status_code == 409
    assert (await api_client.post(f"/api/v1/admin/policies/{policies[0]['id']}/exceptions/{exception_id}/reject", headers=headers)).status_code == 409
    assert (await api_client.post(f"/api/v1/admin/policies/{policies[0]['id']}/exceptions/{exception_id}/revoke", headers=headers)).status_code == 200
    audit = (await api_client.get(f"/api/v1/admin/policies/{policies[0]['id']}/audit?page=1&page_size=100", headers=headers)).json()
    assert audit["items"] == sorted(audit["items"], key=lambda item: (item["created_at"], item["id"]))
    assert any(item["policy_exception_id"] == exception_id for item in audit["items"])
    assert all("rule_definition" not in str(item) and "content" not in str(item) for item in audit["items"])
