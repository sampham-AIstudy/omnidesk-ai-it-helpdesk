"""Read-only applicable-policy API contracts and visibility regression tests."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.auth import get_current_user
from src.database import Base, get_db
from src.main import app
from src.models.policy import Policy, PolicyScope, PolicyVersion
from src.models.user import CompanyUnit, User, UserRole
from src.services.auth_service import hash_password
from src.services.policy_service import deactivate_policy


@pytest_asyncio.fixture
async def api_client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'policy-read.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    users: dict[str, User] = {}
    async with maker() as session:
        specs = [
            ("employee", UserRole.EMPLOYEE, CompanyUnit.AUTOMOTIVE, "sales", True),
            ("technician", UserRole.TECHNICIAN, CompanyUnit.AUTOMOTIVE, "ops", True),
            ("admin", UserRole.ADMIN, CompanyUnit.AUTOMOTIVE, "governance", True),
            ("wrong_department", UserRole.EMPLOYEE, CompanyUnit.AUTOMOTIVE, "finance", True),
            ("other_employee", UserRole.EMPLOYEE, CompanyUnit.AUTOMOTIVE, "sales", True),
            ("health_employee", UserRole.EMPLOYEE, CompanyUnit.HEALTHCARE, "sales", True),
            ("inactive", UserRole.EMPLOYEE, CompanyUnit.AUTOMOTIVE, "sales", False),
        ]
        for username, role, unit, department, active in specs:
            user = User(username=username, email=f"{username}@example.test", full_name=username, hashed_password=hash_password("demo123"), role=role, company_unit=unit, department=department, is_active=active)
            session.add(user)
            users[username] = user
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield {"client": client, "maker": maker, "users": users}
    app.dependency_overrides.clear()
    await engine.dispose()


async def headers(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": "demo123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def add_policy(session: AsyncSession, key: str, *, tenant: str | None = "automotive", scopes: list[dict] | None = None, policy_status: str = "active", version_status: str = "active", effective_from: datetime | None = None, effective_until: datetime | None = None, content: str | None = None, version_number: int = 1) -> Policy:
    now = datetime.now(UTC)
    policy = Policy(policy_key=key, tenant_id=tenant, name=key.replace("-", " "), category="security", description="Safe description", status=policy_status)
    session.add(policy)
    await session.flush()
    version = PolicyVersion(policy_id=policy.id, version_number=version_number, title=key, content=content or f"Approved human policy {key}", rule_definition_json='{"schema_version":1,"default_effect":"advisory","rules":[]}', effect_summary="advisory", priority=1, effective_from=effective_from or now - timedelta(minutes=1), effective_until=effective_until, status=version_status, content_hash=f"hash-{key}-{version_number}")
    session.add(version)
    await session.flush()
    for values in scopes or [{"tenant_id": tenant}]:
        session.add(PolicyScope(policy_version_id=version.id, **values))
    policy.current_version_id = version.id
    await session.commit()
    return policy


@pytest.mark.asyncio
async def test_auth_and_all_active_roles_can_read_matching_policy(api_client):
    client, maker = api_client["client"], api_client["maker"]
    async with maker() as session:
        await add_policy(session, "ROLE-VISIBLE", scopes=[{"tenant_id": "automotive"}])
    assert (await client.get("/api/v1/policies")).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={"username": "inactive", "password": "demo123"})).status_code == 401
    for username in ("employee", "technician", "admin"):
        response = await client.get("/api/v1/policies", headers=await headers(client, username))
        assert response.status_code == 200
        assert [item["policy_key"] for item in response.json()["items"]] == ["ROLE-VISIBLE"]


@pytest.mark.asyncio
async def test_tenant_global_and_detail_enumeration_are_hidden(api_client):
    client, maker = api_client["client"], api_client["maker"]
    async with maker() as session:
        automotive = await add_policy(session, "AUTO-ONLY", scopes=[{"tenant_id": "automotive"}])
        global_policy = await add_policy(session, "GLOBAL-BASELINE", tenant=None, scopes=[{}])
    auto = await headers(client, "employee")
    health = await headers(client, "health_employee")
    assert (await client.get(f"/api/v1/policies/{automotive.id}", headers=health)).status_code == 404
    assert (await client.get(f"/api/v1/policies/{global_policy.id}", headers=auto)).status_code == 200
    assert (await client.get(f"/api/v1/policies/{global_policy.id}", headers=health)).status_code == 200
    health_keys = [item["policy_key"] for item in (await client.get("/api/v1/policies", headers=health)).json()["items"]]
    assert health_keys == ["GLOBAL-BASELINE"]


@pytest.mark.asyncio
async def test_scope_and_or_and_user_visibility(api_client):
    client, maker, users = api_client["client"], api_client["maker"], api_client["users"]
    async with maker() as session:
        both = await add_policy(session, "SALES-EMPLOYEE", scopes=[{"tenant_id": "automotive", "department": "sales", "role": "employee"}])
        either = await add_policy(session, "SALES-OR-TECH", scopes=[{"tenant_id": "automotive", "department": "sales"}, {"tenant_id": "automotive", "role": "technician"}])
        user_only = await add_policy(session, "USER-ONLY", scopes=[{"tenant_id": "automotive", "user_id": users["employee"].id}])
    employee = await headers(client, "employee")
    wrong_department = await headers(client, "wrong_department")
    technician = await headers(client, "technician")
    other = await headers(client, "other_employee")
    assert (await client.get(f"/api/v1/policies/{both.id}", headers=employee)).status_code == 200
    assert (await client.get(f"/api/v1/policies/{both.id}", headers=wrong_department)).status_code == 404
    assert (await client.get(f"/api/v1/policies/{both.id}", headers=technician)).status_code == 404
    assert (await client.get(f"/api/v1/policies/{either.id}", headers=employee)).status_code == 200
    assert (await client.get(f"/api/v1/policies/{either.id}", headers=technician)).status_code == 200
    assert (await client.get(f"/api/v1/policies/{user_only.id}", headers=employee)).status_code == 200
    assert (await client.get(f"/api/v1/policies/{user_only.id}", headers=other)).status_code == 404


@pytest.mark.asyncio
async def test_state_windows_current_version_and_deactivation(api_client):
    client, maker, users = api_client["client"], api_client["maker"], api_client["users"]
    now = datetime.now(UTC)
    async with maker() as session:
        draft = await add_policy(session, "DRAFT", policy_status="draft")
        approved = await add_policy(session, "APPROVED", version_status="approved")
        future = await add_policy(session, "FUTURE", effective_from=now + timedelta(days=1))
        expired = await add_policy(session, "EXPIRED", effective_from=now - timedelta(days=2), effective_until=now - timedelta(days=1))
        inactive = await add_policy(session, "INACTIVE", policy_status="inactive")
        archived = await add_policy(session, "ARCHIVED", policy_status="archived")
        current = await add_policy(session, "CURRENT", content="Current approved text", version_number=2)
        old = PolicyVersion(policy_id=current.id, version_number=1, title="old", content="Old secret text", rule_definition_json='{"schema_version":1,"default_effect":"advisory","rules":[]}', effect_summary="advisory", priority=1, effective_from=now - timedelta(days=2), status="superseded", content_hash="old-hash")
        session.add(old)
        await session.commit()
        deactivated = await add_policy(session, "DEACTIVATE")
        await deactivate_policy(session, actor_id=users["admin"].id, tenant_id="automotive", global_admin=True, policy_id=deactivated.id)
        await session.commit()
    employee = await headers(client, "employee")
    for policy in (draft, approved, future, expired, inactive, archived, deactivated):
        assert (await client.get(f"/api/v1/policies/{policy.id}", headers=employee)).status_code == 404
    detail = (await client.get(f"/api/v1/policies/{current.id}", headers=employee)).json()
    assert detail["current_version_number"] == 2 and detail["content"] == "Current approved text"


@pytest.mark.asyncio
async def test_pagination_filters_hidden_totals_and_response_privacy(api_client):
    client, maker = api_client["client"], api_client["maker"]
    async with maker() as session:
        await add_policy(session, "ALPHA-ONE")
        await add_policy(session, "ALPHA-TWO")
        await add_policy(session, "ALPHA-HIDDEN", tenant="healthcare", scopes=[{"tenant_id": "healthcare"}])
    response = await client.get("/api/v1/policies?page=1&page_size=1&query=ALPHA&category=security", headers=await headers(client, "employee"))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2 and len(body["items"]) == 1
    second = await client.get("/api/v1/policies?page=2&page_size=1&query=ALPHA", headers=await headers(client, "employee"))
    assert second.status_code == 200 and len(second.json()["items"]) == 1
    for suffix in ("page=0", "page_size=0", "page_size=101"):
        assert (await client.get(f"/api/v1/policies?{suffix}", headers=await headers(client, "employee"))).status_code == 422
    forbidden = {"rule_definition_json", "audit", "exceptions", "created_by", "approved_by", "activated_by", "content_hash", "tenant_id", "supersedes_version_id"}
    assert not forbidden.intersection(body["items"][0])


@pytest.mark.asyncio
async def test_openapi_has_exact_read_routes(api_client):
    paths = (await api_client["client"].get("/openapi.json")).json()["paths"]
    assert set(paths["/api/v1/policies"]) == {"get"}
    assert set(paths["/api/v1/policies/{policy_id}"]) == {"get"}
