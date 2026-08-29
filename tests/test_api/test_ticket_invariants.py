"""
Business Invariants Automated Test Suite
Verifies strict Enterprise Help Desk Invariants:
1. Ambiguous user responses ("ok để tôi thử", "có vẻ được") NEVER trigger AI auto-closure.
2. Dissatisfaction user responses ("vẫn lỗi", "chưa được", "không đúng") MUST trigger Human Handoff.
3. Explicit Agent Takeover (POST /tickets/{id}/takeover) assigns technician and transitions state.
4. Empty reopen reason is rejected with HTTP 400.
5. Invalid rating (< 1 or > 5) is rejected with HTTP 422.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ambiguous_response_does_not_close_ticket(
    client: AsyncClient,
    auth_employee: str,
):
    """Test that ambiguous user phrases ('ok để tôi thử', 'có vẻ được') do NOT auto-close ticket."""
    headers = {"Authorization": f"Bearer {auth_employee}"}

    # Create ticket
    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Lỗi kết nối Wi-Fi", "description": "Không thể kết nối Wi-Fi văn phòng"},
        headers=headers,
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["ticket_id"]

    # Send ambiguous message
    msg_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"message": "ok để tôi thử cách này xem sao"},
        headers=headers,
    )
    assert msg_res.status_code == 200

    # Verify ticket is NOT closed
    ticket_res = await client.get(f"/api/v1/tickets/{ticket_id}", headers=headers)
    assert ticket_res.status_code == 200
    status = ticket_res.json()["status"]
    assert status not in ("closed", "resolved")


@pytest.mark.asyncio
async def test_dissatisfaction_triggers_human_handoff(
    client: AsyncClient,
    auth_employee: str,
):
    """Test that dissatisfaction ('vẫn lỗi', 'chưa được', 'không đúng') triggers Human Handoff."""
    headers = {"Authorization": f"Bearer {auth_employee}"}

    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Lỗi ứng dụng Outlook", "description": "Outlook bị đơ khi gửi email"},
        headers=headers,
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["ticket_id"]

    # User expresses dissatisfaction
    msg_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"message": "Tôi đã làm theo nhưng vẫn lỗi không gửi được"},
        headers=headers,
    )
    assert msg_res.status_code == 200

    # Verify status changed to waiting_for_agent or escalated
    ticket_res = await client.get(f"/api/v1/tickets/{ticket_id}", headers=headers)
    assert ticket_res.status_code == 200
    t_data = ticket_res.json()
    assert t_data["status"] in ("waiting_for_agent", "escalated")
    assert t_data["support_mode"] == "ai"


@pytest.mark.asyncio
async def test_waiting_ticket_always_gets_a_fallback_agent_reply(
    client: AsyncClient,
    auth_employee: str,
):
    """A queued ticket must not silently save an employee message."""
    headers = {"Authorization": f"Bearer {auth_employee}"}
    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Can cai dat phan mem noi bo", "description": "Can huong dan cai dat phan mem da duoc cap phep"},
        headers=headers,
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["ticket_id"]

    queued = await client.post(f"/api/v1/tickets/{ticket_id}/request-technician", headers=headers)
    assert queued.status_code == 200

    with (
        patch("src.services.ticket_conversation_service.search_similar", return_value=[]),
        patch("src.services.ticket_conversation_service.has_actionable_external_context", return_value=False),
        patch("src.services.zero_mem_service.retrieve_episodic_evidence", AsyncMock(return_value=([], {}))),
        patch("src.services.zero_mem_service.audit_memory_retrieval", AsyncMock()),
    ):
        response = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages/stream",
            json={"message": "Phan mem con loi, toi can bo sung thong tin gi?"},
            headers=headers,
        )

    assert response.status_code == 200
    assert "event: token" in response.text
    assert "event: done" in response.text
    messages_response = await client.get(f"/api/v1/tickets/{ticket_id}/messages", headers=headers)
    assert messages_response.status_code == 200
    messages = messages_response.json()["items"]
    assert messages[-2]["sender_type"] == "user"
    assert messages[-1]["sender_type"] == "agent"
    assert "Ticket c\u1ee7a b\u1ea1n \u0111ang ch\u1edd chuy\u00ean vi\u00ean" in messages[-1]["content"]


@pytest.mark.asyncio
async def test_technician_takeover_api(
    client: AsyncClient,
    auth_employee: str,
    auth_technician: str,
):
    """Test explicit technician takeover (POST /tickets/{id}/takeover)."""
    emp_headers = {"Authorization": f"Bearer {auth_employee}"}
    mgr_headers = {"Authorization": f"Bearer {auth_technician}"}

    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Màn hình xanh BSOD", "description": "Lỗi 0x80070005 khẩn cấp"},
        headers=emp_headers,
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["ticket_id"]

    # Technician claims takeover
    takeover_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/takeover",
        headers=mgr_headers,
    )
    assert takeover_res.status_code == 200
    t_data = takeover_res.json()
    assert t_data["status"] in ("in_progress", "human_active")
    assert t_data["support_mode"] == "human"
    assert t_data["assignee_id"] is not None


@pytest.mark.asyncio
async def test_empty_reopen_reason_rejected(
    client: AsyncClient,
    auth_employee: str,
):
    """Test that empty reopen reason returns HTTP 400 or 422."""
    headers = {"Authorization": f"Bearer {auth_employee}"}

    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Hỗ trợ phần mềm ERP", "description": "Không mở được báo cáo SAP"},
        headers=headers,
    )
    ticket_id = create_res.json()["ticket_id"]

    # Close ticket first
    await client.post(f"/api/v1/tickets/{ticket_id}/close", headers=headers)

    # Attempt to reopen with empty reason
    reopen_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/reopen",
        json={"reason": "   "},
        headers=headers,
    )
    assert reopen_res.status_code in (400, 422)


@pytest.mark.asyncio
async def test_ticket_reopens_with_reason(
    client: AsyncClient,
    auth_employee: str,
):
    """A valid reopen request must bind its JSON body and reopen the ticket."""
    headers = {"Authorization": f"Bearer {auth_employee}"}
    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Káº¿t ná»‘i VPN váº«n lá»—i", "description": "KhÃ´ng thá»ƒ truy cáº­p táº§ng nguyá»“n ná»™i bá»™ sau khi Ä‘Ã³ng ticket."},
        headers=headers,
    )
    ticket_id = create_res.json()["ticket_id"]
    await client.post(f"/api/v1/tickets/{ticket_id}/close", headers=headers)

    reopen_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/reopen",
        json={"reason": "Sá»± cá»‘ váº«n táº¡i diá»…n sau khi Ã¡p dá»¥ng hÆ°á»›ng dáº«n."},
        headers=headers,
    )

    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] in ("reopened", "waiting_for_agent", "human_active")


@pytest.mark.asyncio
async def test_ticket_rating_is_saved(
    client: AsyncClient,
    auth_employee: str,
):
    """A valid post-resolution rating must be persisted on the ticket."""
    headers = {"Authorization": f"Bearer {auth_employee}"}
    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "ÄÃ¡nh giÃ¡ há»— trá»£", "description": "Kiá»ƒm tra lÆ°u Ä‘Ã¡nh giÃ¡ sau khi Ä‘Ã³ng ticket."},
        headers=headers,
    )
    ticket_id = create_res.json()["ticket_id"]
    await client.post(f"/api/v1/tickets/{ticket_id}/close", headers=headers)

    rating_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/rating",
        json={"rating": 5, "feedback": "ÄÃ£ xá»­ lÃ½ nhanh vÃ  Ä‘Ãºng váº¥n Ä‘á»."},
        headers=headers,
    )

    assert rating_res.status_code == 200
    assert rating_res.json()["rating"] == 5
    assert rating_res.json()["rating_feedback"] == "ÄÃ£ xá»­ lÃ½ nhanh vÃ  Ä‘Ãºng váº¥n Ä‘á»."


@pytest.mark.asyncio
async def test_invalid_rating_rejected(
    client: AsyncClient,
    auth_employee: str,
):
    """Test that rating outside 1-5 range returns HTTP 422."""
    headers = {"Authorization": f"Bearer {auth_employee}"}

    create_res = await client.post(
        "/api/v1/tickets",
        json={"title": "Hỗ trợ tài khoản M365", "description": "Cần mở khóa SSPR"},
        headers=headers,
    )
    ticket_id = create_res.json()["ticket_id"]

    # Close ticket
    await client.post(f"/api/v1/tickets/{ticket_id}/close", headers=headers)

    # Attempt rating 10
    rating_res = await client.post(
        f"/api/v1/tickets/{ticket_id}/rating",
        json={"rating": 10, "feedback": "Tuyệt vời"},
        headers=headers,
    )
    assert rating_res.status_code == 422
