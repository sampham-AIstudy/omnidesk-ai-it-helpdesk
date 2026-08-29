"""Integration tests for technician join endpoint idempotency in src.api.tickets."""
import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_technician_join_idempotency(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "tech1", "password": "demo123"})
    if resp.status_code != 200:
        pytest.skip("tech1 user login not available in test environment")
    technician_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

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

    join_res1 = await client.post(f"/api/v1/tickets/{ticket_id}/join", headers=technician_headers)
    assert join_res1.status_code == 200
    messages1 = join_res1.json()["items"]
    system_join_messages1 = [
        m for m in messages1
        if m["sender_type"] == "system" and "CHUYÊN VIÊN THAM GIA" in m["content"]
    ]
    assert len(system_join_messages1) == 1

    join_res2 = await client.post(f"/api/v1/tickets/{ticket_id}/join", headers=technician_headers)
    assert join_res2.status_code == 200
    messages2 = join_res2.json()["items"]
    system_join_messages2 = [
        m for m in messages2
        if m["sender_type"] == "system" and "CHUYÊN VIÊN THAM GIA" in m["content"]
    ]
    assert len(system_join_messages2) == 1, "Duplicate join announcement was created on repeat join"


@pytest.mark.asyncio
async def test_technician_join_concurrent_requests(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "tech1", "password": "demo123"})
    if resp.status_code != 200:
        pytest.skip("tech1 user login not available in test environment")
    technician_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

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
        client.post(f"/api/v1/tickets/{ticket_id}/join", headers=technician_headers),
        client.post(f"/api/v1/tickets/{ticket_id}/join", headers=technician_headers),
    )
    assert res1.status_code == 200
    assert res2.status_code == 200

    messages = res2.json()["items"]
    system_join_messages = [
        m for m in messages
        if m["sender_type"] == "system" and "CHUYÊN VIÊN THAM GIA" in m["content"]
    ]
    assert len(system_join_messages) == 1, "Concurrent joins created duplicate announcements"
