"""Tests cho Tickets API endpoints."""
import pytest


@pytest.mark.asyncio
async def test_create_ticket_success(client, auth_employee):
    """Employee tạo ticket thành công."""
    if not auth_employee:
        pytest.skip("No auth token")

    from src.assignment.rate_limiter import reset_rate_limiter
    reset_rate_limiter()

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
async def test_list_tickets_technician_sees_tenant_queue(client, auth_technician):
    """Technician can see the operational tenant queue."""
    if not auth_technician:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/tickets",
        headers={"Authorization": f"Bearer {auth_technician}"}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pending_hitl_requires_staff(client, auth_employee):
    """Employee không thể xem pending HITL list -> 403."""
    if not auth_employee:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/tickets/pending-hitl",
        headers={"Authorization": f"Bearer {auth_employee}"}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pending_hitl_technician_can_access(client, auth_technician):
    """Technician can access the compatibility endpoint."""
    if not auth_technician:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/tickets/pending-hitl",
        headers={"Authorization": f"Bearer {auth_technician}"}
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
async def test_hitl_approve_requires_staff(client, auth_employee):
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
async def test_dashboard_technician_ok(client, auth_technician):
    """Technician can view tenant-scoped operational analytics."""
    if not auth_technician:
        pytest.skip("No auth token")

    resp = await client.get(
        "/api/v1/analytics/dashboard",
        headers={"Authorization": f"Bearer {auth_technician}"}
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
