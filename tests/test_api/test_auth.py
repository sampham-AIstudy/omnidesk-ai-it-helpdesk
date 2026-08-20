"""Tests cho Auth API endpoints."""
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health check phải trả 200."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client):
    """Đăng nhập thành công → trả về token và user."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "employee1",
        "password": "demo123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "employee1"
    assert data["user"]["role"] == "employee"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Mật khẩu sai → 401."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "employee1",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    """User không tồn tại → 401."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "nonexistent",
        "password": "demo123"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client, auth_employee):
    """GET /me với token hợp lệ → user info."""
    if not auth_employee:
        pytest.skip("No auth token available")

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_employee}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "employee1"
    assert data["role"] == "employee"


@pytest.mark.asyncio
async def test_me_no_token(client):
    """GET /me không có token → 401 Unauthorized (HTTPBearer standard)."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    """GET /me token giả → 401."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_manager_has_correct_role(client):
    """Manager login → role = manager."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "manager1",
        "password": "demo123"
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "manager"
