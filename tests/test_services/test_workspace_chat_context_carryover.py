"""Regression tests for Workspace Chat multi-turn contextual query resolution.

Verifies:
1. "thông tin" -> "về giám đốc": resolves to third-party information intent and triggers privacy refusal.
2. "tôi bị hỏng cục" -> "cục wifi": second turn uses first-turn context and does not ask for clarification again.
3. "VPN của tôi lỗi" -> "nó vẫn không vào được": referent "nó" resolves to VPN issue.
4. "cho tôi thông tin của giám đốc" -> privacy refusal -> "thông tin của tôi": previous third-party referent does NOT contaminate self-profile query.
5. Conversation A context must NOT appear in Conversation B.
6. REST and SSE must resolve the same follow-up identically.
"""
from __future__ import annotations

import json
import unicodedata
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.services.auth_service import create_access_token
from src.services.context_query_service import resolve_contextual_user_query
from src.services.recent_conversation_context import RecentConversationMessage


class _MockChunk:
    def __init__(self, content: str):
        self.content = content


def _create_mock_llm(reply_text: str):
    mock = MagicMock()
    mock.model = "mistral-mock"
    mock.ainvoke = AsyncMock(return_value=MagicMock(content=reply_text))

    async def _mock_astream(*args, **kwargs):
        yield _MockChunk(reply_text)

    mock.astream = _mock_astream
    return mock


@pytest.fixture(autouse=True)
def _mock_offline_chat_dependencies():
    from src.services.web_research_service import ResearchResult

    empty_research = ResearchResult(False, "web_search_not_triggered", None, [])
    mock_rag_reply = "Chào bạn, hệ thống đã ghi nhận thông tin và hướng dẫn xử lý sự cố thiết bị Wi-Fi."
    mock_llm = _create_mock_llm(mock_rag_reply)
    mock_fast_llm = _create_mock_llm('{"is_complex": false, "sub_queries": []}')

    with (
        patch("src.api.chat.get_rag_llm", return_value=mock_llm),
        patch("src.services.query_decomposition_service.get_fast_classifier_llm", return_value=mock_fast_llm),
        patch("src.api.chat.maybe_research_web", new=AsyncMock(return_value=empty_research)),
    ):
        yield


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").replace("đ", "d")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_case_1_thong_tin_followed_by_ve_giam_doc_triggers_privacy_refusal(client: AsyncClient):
    """Case 1: 'thông tin' -> 'về giám đốc' must resolve to 'thông tin về giám đốc' and trigger privacy refusal."""
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    # 1. Unit resolution check
    history = [
        RecentConversationMessage("m1", "user", "thông tin"),
        RecentConversationMessage("m2", "assistant", "Vui lòng mô tả thêm thiết bị hoặc dịch vụ..."),
    ]
    res = resolve_contextual_user_query("về giám đốc", recent_history=history)
    assert res.is_rewritten is True
    assert "thông tin" in res.resolved_query and "giám đốc" in res.resolved_query

    # 2. Integration API check
    create_resp = await client.post("/api/v1/chat/conversations", json={"title": "Privacy Test"}, headers=headers)
    conv_id = create_resp.json()["id"]

    r1 = await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "thông tin"}, headers=headers)
    assert r1.status_code == 200

    r2 = await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "về giám đốc"}, headers=headers)
    assert r2.status_code == 200
    reply = r2.json()["reply"]
    folded = _fold(reply)
    assert "quyen rieng tu" in folded or "khong the tim hoac tiet lo" in folded or "chi co the xem thong tin ho so" in folded
    assert r2.json()["answerability"] == "unanswerable"


@pytest.mark.asyncio
async def test_case_2_entity_clarification_tai_bi_hong_cuc_followed_by_cuc_wifi(client: AsyncClient):
    """Case 2: 'tôi bị hỏng cục' -> 'cục wifi' resolves to broken wifi device context without repeating clarification request."""
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    # 1. Unit resolution check
    history = [
        RecentConversationMessage("m1", "user", "tôi bị hỏng cục"),
        RecentConversationMessage("m2", "assistant", "Mình có thể hỗ trợ, và bạn không cần biết tên lỗi. Hãy cho mình biết..."),
    ]
    res = resolve_contextual_user_query("cục wifi", recent_history=history)
    assert res.is_rewritten is True
    assert "tôi bị hỏng cục wifi" in res.resolved_query or ("hỏng cục" in res.resolved_query and "wifi" in res.resolved_query)

    # 2. Integration API check
    create_resp = await client.post("/api/v1/chat/conversations", json={"title": "Broken Device Flow"}, headers=headers)
    conv_id = create_resp.json()["id"]

    r1 = await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "tôi bị hỏng cục"}, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["answerability"] == "needs_clarification"

    r2 = await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "cục wifi"}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["answerability"] != "needs_clarification"


@pytest.mark.asyncio
async def test_case_3_vpn_loi_followed_by_no_van_khong_vao_duoc(client: AsyncClient):
    """Case 3: 'VPN của tôi lỗi' -> 'nó vẫn không vào được' resolves 'nó' as VPN issue."""
    history = [
        RecentConversationMessage("m1", "user", "VPN của tôi lỗi"),
        RecentConversationMessage("m2", "assistant", "Bạn vui lòng kiểm tra kết nối mạng."),
    ]
    res = resolve_contextual_user_query("nó vẫn không vào được", recent_history=history)
    assert res.is_rewritten is True
    assert "VPN" in res.resolved_query


@pytest.mark.asyncio
async def test_case_4_third_party_refusal_does_not_contaminate_subsequent_self_profile(client: AsyncClient):
    """Case 4: 'cho tôi thông tin của giám đốc' (refusal) -> 'thông tin của tôi' (must return self-profile without contamination)."""
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    create_resp = await client.post("/api/v1/chat/conversations", json={"title": "Profile Separation"}, headers=headers)
    conv_id = create_resp.json()["id"]

    # Turn 1: Third-party request -> refused
    r1 = await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "cho tôi thông tin của giám đốc"}, headers=headers)
    assert r1.status_code == 200
    assert "khong the" in _fold(r1.json()["reply"]) or "quyen rieng tu" in _fold(r1.json()["reply"])

    # Turn 2: Self profile inquiry -> returns authenticated user profile
    r2 = await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "thông tin của tôi"}, headers=headers)
    assert r2.status_code == 200
    reply = r2.json()["reply"]
    assert "Hồ sơ tài khoản" in reply or "Email:" in reply or "Vai trò:" in reply
    assert r2.json()["answerability"] == "evidence_available"


@pytest.mark.asyncio
async def test_case_5_cross_conversation_isolation(client: AsyncClient):
    """Case 5: Context from Conversation A must NOT leak into Conversation B."""
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    # Create Conv A & Conv B
    conv_a = (await client.post("/api/v1/chat/conversations", json={"title": "Conv A"}, headers=headers)).json()["id"]
    conv_b = (await client.post("/api/v1/chat/conversations", json={"title": "Conv B"}, headers=headers)).json()["id"]

    # In Conv A: user says "thông tin"
    await client.post(f"/api/v1/chat/conversations/{conv_a}/messages", json={"message": "thông tin"}, headers=headers)

    # In Conv B: user asks "cục wifi"
    r_b = await client.post(f"/api/v1/chat/conversations/{conv_b}/messages", json={"message": "cục wifi"}, headers=headers)
    assert r_b.status_code == 200
    # Conv B should have no memory of "thông tin" from Conv A
    b_history = (await client.get(f"/api/v1/chat/conversations/{conv_b}", headers=headers)).json()["messages"]
    assert not any("thông tin" == m["content"] for m in b_history)


@pytest.mark.asyncio
async def test_case_6_rest_and_sse_followup_parity(client: AsyncClient):
    """Case 6: REST and SSE must resolve follow-up queries identically."""
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    create_resp = await client.post("/api/v1/chat/conversations", json={"title": "Parity Test"}, headers=headers)
    conv_id = create_resp.json()["id"]

    # Turn 1: "thông tin"
    await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "thông tin"}, headers=headers)

    # Turn 2 REST with conversation_id
    rest_resp = await client.post("/api/v1/chat", json={"message": "về giám đốc", "conversation_id": conv_id}, headers=headers)
    assert rest_resp.status_code == 200
    assert rest_resp.json()["answerability"] == "unanswerable"

    # Turn 2 SSE with conversation_id
    sse_resp = await client.post("/api/v1/chat/stream", json={"message": "về giám đốc", "conversation_id": conv_id}, headers=headers)
    assert sse_resp.status_code == 200
    lines = sse_resp.text.split("\n")
    done_payload = None
    for line in lines:
        if line.startswith("data: "):
            try:
                parsed = json.loads(line[6:])
                if "reply" in parsed:
                    done_payload = parsed
            except json.JSONDecodeError:
                pass
    assert done_payload is not None
    assert done_payload["answerability"] == "unanswerable"
    assert _fold(done_payload["reply"]) == _fold(rest_resp.json()["reply"])


@pytest.mark.asyncio
async def test_case_7_vpn_khong_vao_followed_by_no_van_timeout():
    """Case 7 / C: 'VPN không vào' -> 'nó vẫn timeout' resolves referent 'nó' and 'timeout' to VPN context."""
    history = [
        RecentConversationMessage("m1", "user", "VPN không vào được từ sáng nay"),
        RecentConversationMessage("m2", "assistant", "Bạn hãy thử kiểm tra cấu hình mạng."),
    ]
    res = resolve_contextual_user_query("nó vẫn timeout", recent_history=history)
    assert res.is_rewritten is True
    assert "VPN" in res.resolved_query
    assert "timeout" in res.resolved_query


@pytest.mark.asyncio
async def test_case_8_port_403_followed_by_cong_do_thi_sao():
    """Case 8 / D: 'port 403 không vào' -> 'cổng đó thì sao' retains port 403 referent."""
    history = [
        RecentConversationMessage("m1", "user", "tôi thấy tôi đã ping thành công đến 10.0.0.1 tại sao không kết nối được đến port 403"),
        RecentConversationMessage("m2", "assistant", "Cổng 403 có thể bị chặn bởi tường lửa hoặc proxy."),
    ]
    res = resolve_contextual_user_query("cổng đó thì sao", recent_history=history)
    assert res.is_rewritten is True
    assert "403" in res.resolved_query or "port" in res.resolved_query.lower()


@pytest.mark.asyncio
async def test_case_9_port_403_followed_by_social_topic_shift_in_ticket():
    """Case 9 / E: In ticket chat, 'port 403' discussion followed by 'tôi buồn quá' must NOT replay technical troubleshooting."""
    from src.database import AsyncSessionLocal
    from src.models.ticket import Ticket, TicketStatus
    from src.models.ticket_message import TicketMessageSender
    from src.models.user import User
    from src.services.ticket_conversation_service import add_message, handle_ticket_message

    async with AsyncSessionLocal() as db:
        owner = (await db.execute(select(User).order_by(User.id))).scalars().first()
        ticket = Ticket(
            ticket_number="TCK-PORT-403",
            title="Sự cố kết nối VPN và cổng 403",
            description="Ping 10.0.0.1 được nhưng cổng 403 bị từ chối kết nối",
            submitter_id=owner.id,
            status=TicketStatus.OPEN,
        )
        db.add(ticket)
        await db.flush()

        # Turn 1: User technical question + assistant technical response
        await add_message(
            db,
            ticket_id=ticket.id,
            sender_type=TicketMessageSender.USER,
            sender_id=owner.id,
            content="tôi thấy tôi đã ping thành công đến 10.0.0.1 tại sao không kết nối được đến cổng 403",
        )
        await add_message(
            db,
            ticket_id=ticket.id,
            sender_type=TicketMessageSender.AGENT,
            content="Hiện tại chưa có đủ dữ liệu để xác định chính xác nguyên nhân chặn cổng 403.",
        )
        await db.commit()

        # Turn 2: User says "tôi buồn quá"
        with (
            patch("src.services.ticket_conversation_service.search_similar") as mock_search,
            patch("src.services.ticket_conversation_service.get_rag_llm") as mock_rag_llm,
        ):
            messages = await handle_ticket_message(
                db,
                ticket=ticket,
                user=owner,
                content="tôi buồn quá",
            )

        # Assert no vector search was performed and no technical RAG LLM was called
        mock_search.assert_not_called()
        mock_rag_llm.assert_not_called()

        # Assert agent reply acknowledges feeling naturally without replaying port 80/403/VPN troubleshooting
        latest_reply = messages[-1].content
        folded_reply = _fold(latest_reply)
        assert "met moi" in folded_reply or "tro ngai" in folded_reply or "san sang" in folded_reply or "ho tro" in folded_reply
        assert "port 80" not in latest_reply and "cổng 80" not in latest_reply
        assert "mpls" not in latest_reply.lower()
        # Ticket status remains open/active without premature closure or handoff
        assert ticket.status == TicketStatus.OPEN


@pytest.mark.asyncio
async def test_case_10_two_different_tickets_history_isolation():
    """Case 10 / H: History from Ticket A must not appear in Ticket B."""
    from src.database import AsyncSessionLocal
    from src.models.ticket import Ticket, TicketStatus
    from src.models.ticket_message import TicketMessageSender
    from src.models.user import User
    from src.services.recent_conversation_context import load_ticket_recent_history
    from src.services.ticket_conversation_service import add_message

    async with AsyncSessionLocal() as db:
        owner = (await db.execute(select(User).order_by(User.id))).scalars().first()
        ticket_a = Ticket(ticket_number="TCK-ISO-A", title="Ticket A", description="Desc A", submitter_id=owner.id, status=TicketStatus.OPEN)
        ticket_b = Ticket(ticket_number="TCK-ISO-B", title="Ticket B", description="Desc B", submitter_id=owner.id, status=TicketStatus.OPEN)
        db.add_all([ticket_a, ticket_b])
        await db.flush()

        await add_message(db, ticket_id=ticket_a.id, sender_type=TicketMessageSender.USER, sender_id=owner.id, content="TICKET_A_SECRET_KEY")
        await add_message(db, ticket_id=ticket_b.id, sender_type=TicketMessageSender.USER, sender_id=owner.id, content="TICKET_B_NORMAL_MSG")
        await db.commit()

        history_b = await load_ticket_recent_history(db, ticket_id=ticket_b.id, exclude_message_id=None)
        assert not any("TICKET_A_SECRET_KEY" in m.content for m in history_b)
        assert any("TICKET_B_NORMAL_MSG" in m.content for m in history_b)


@pytest.mark.asyncio
async def test_case_11_turn_correlation_and_causal_attachment(client: AsyncClient):
    """Case 11 / F: Each response is causally associated with its triggering user turn in conversation history."""
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    create_resp = await client.post("/api/v1/chat/conversations", json={"title": "Turn Correlation"}, headers=headers)
    conv_id = create_resp.json()["id"]

    # Turn 1
    r1 = await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "thông tin"}, headers=headers)
    assert r1.status_code == 200

    # Turn 2
    r2 = await client.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"message": "về giám đốc"}, headers=headers)
    assert r2.status_code == 200

    # Fetch conversation transcript and verify exact turn sequence: U1 -> A1 -> U2 -> A2
    conv_detail = (await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers)).json()
    msgs = conv_detail["messages"]
    assert len(msgs) == 4
    assert msgs[0]["role"] == "user" and msgs[0]["content"] == "thông tin"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "user" and msgs[2]["content"] == "về giám đốc"
    assert msgs[3]["role"] == "assistant"
    assert "quyen rieng tu" in _fold(msgs[3]["content"]) or "khong the" in _fold(msgs[3]["content"])
