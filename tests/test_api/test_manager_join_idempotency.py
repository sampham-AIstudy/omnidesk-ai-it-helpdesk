"""Integration tests for manager join endpoint idempotency in src.api.tickets."""
import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from src.models.user import User, UserRole


@pytest.mark.asyncio
async def test_manager_join_idempotency(client: AsyncClient):
    # Log in as manager
    resp = await client.post("/api/v1/auth/login", json={"username": "manager1", "password": "demo123"})
    if resp.status_code != 200:
        pytest.skip("manager1 user login not available in test environment")
    manager_token = resp.json()["access_token"]
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    # Log in as employee to create ticket
    emp_resp = await client.post("/api/v1/auth/login", json={"username": "employee1", "password": "demo123"})
    assert emp_resp.status_code == 200
    emp_token = emp_resp.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Create ticket
    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Sự cố mạng văn phòng", "description": "Mất kết nối mạng tầng 3"},
        headers=emp_headers,
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["ticket_id"]

    # First join call by manager
    join_res1 = await client.post(f"/api/v1/tickets/{ticket_id}/join", headers=manager_headers)
    assert join_res1.status_code == 200
    messages1 = join_res1.json()["items"]
    system_join_messages1 = [
        m for m in messages1
        if m["sender_type"] == "system" and "QUẢN LÝ THAM GIA" in m["content"]
    ]
    assert len(system_join_messages1) == 1

    # Second join call by the same manager (idempotency check)
    join_res2 = await client.post(f"/api/v1/tickets/{ticket_id}/join", headers=manager_headers)
    assert join_res2.status_code == 200
    messages2 = join_res2.json()["items"]
    system_join_messages2 = [
        m for m in messages2
        if m["sender_type"] == "system" and "QUẢN LÝ THAM GIA" in m["content"]
    ]
    assert len(system_join_messages2) == 1, "Duplicate join announcement was created on repeat join"


@pytest.mark.asyncio
async def test_manager_join_concurrent_requests(client: AsyncClient):
    # Log in as manager
    resp = await client.post("/api/v1/auth/login", json={"username": "manager1", "password": "demo123"})
    if resp.status_code != 200:
        pytest.skip("manager1 user login not available in test environment")
    manager_token = resp.json()["access_token"]
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    # Log in as employee to create ticket
    emp_resp = await client.post("/api/v1/auth/login", json={"username": "employee1", "password": "demo123"})
    assert emp_resp.status_code == 200
    emp_token = emp_resp.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Create ticket
    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Sự cố ứng dụng ERP", "description": "Không thể đăng nhập hệ thống ERP"},
        headers=emp_headers,
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["ticket_id"]

    # Concurrently send two join requests for the same ticket
    res1, res2 = await asyncio.gather(
        client.post(f"/api/v1/tickets/{ticket_id}/join", headers=manager_headers),
        client.post(f"/api/v1/tickets/{ticket_id}/join", headers=manager_headers),
    )
    assert res1.status_code == 200
    assert res2.status_code == 200

    messages = res2.json()["items"]
    system_join_messages = [
        m for m in messages
        if m["sender_type"] == "system" and "QUẢN LÝ THAM GIA" in m["content"]
    ]
    assert len(system_join_messages) == 1, "Concurrent joins created duplicate announcements"
