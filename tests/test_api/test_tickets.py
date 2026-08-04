"""Tests cho Tickets API endpoints."""
import pytest


@pytest.mark.asyncio
async def test_create_ticket_success(client, auth_employee):
    """Employee tạo ticket thành công."""
    if not auth_employee:
        pytest.skip("No auth token")

    resp = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Test: Không kết nối được mạng",
            "description": "Máy tính không vào được internet từ sáng. Đã thử restart router nhưng không được.",
            "is_production_impact": False,
        },
        headers={"Authorization": f"Bearer {auth_employee}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticket_number"].startswith("INC-")
    assert data["action_taken"] == "processing"
    assert "ticket_id" in data


@pytest.mark.asyncio
async def test_create_ticket_unauthenticated(client):
    """Tạo ticket không có auth → 401 Unauthorized (HTTPBearer)."""
    resp = await client.post(
        "/api/v1/tickets",
        json={"title": "Test", "description": "Test description without auth", "is_production_impact": False}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_tickets_employee(client, auth_employee):
    """Employee chỉ thấy ticket của mình."""
    if not auth_employee:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/tickets",
        headers={"Authorization": f"Bearer {auth_employee}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_tickets_manager_sees_all(client, auth_manager):
    """Manager thấy tất cả ticket."""
    if not auth_manager:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/tickets",
        headers={"Authorization": f"Bearer {auth_manager}"}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pending_hitl_requires_manager(client, auth_employee):
    """Employee không thể xem pending HITL list -> 403."""
    if not auth_employee:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/tickets/pending-hitl",
        headers={"Authorization": f"Bearer {auth_employee}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_pending_hitl_manager_can_access(client, auth_manager):
    """Manager có thể xem pending HITL list."""
    if not auth_manager:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/tickets/pending-hitl",
        headers={"Authorization": f"Bearer {auth_manager}"}
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_ticket_not_found(client, auth_employee):
    """Ticket không tồn tại → 404."""
    if not auth_employee:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/tickets/99999",
        headers={"Authorization": f"Bearer {auth_employee}"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hitl_approve_requires_manager(client, auth_employee):
    """Employee không thể approve HITL ticket -> 403."""
    if not auth_employee:
        pytest.skip("No auth token")

    resp = await client.post(
        "/api/v1/tickets/1/approve",
        json={"approved": True, "note": "Test"},
        headers={"Authorization": f"Bearer {auth_employee}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    """Analytics dashboard không có auth → 401 Unauthorized."""
    resp = await client.get("/api/v1/analytics/dashboard")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_manager_ok(client, auth_manager):
    """Manager có thể xem dashboard."""
    if not auth_manager:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/analytics/dashboard",
        headers={"Authorization": f"Bearer {auth_manager}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "classification" in data
    assert "sla" in data
    assert "recent_tickets" in data
    assert "pending_hitl" in data


@pytest.mark.asyncio
async def test_health_kb_stats(client):
    """Health endpoint báo số KB documents."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "kb_documents" in data
    assert isinstance(data["kb_documents"], int)
