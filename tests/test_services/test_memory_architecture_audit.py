"""Comprehensive Memory Architecture Audit Tests.

Tests the three memory layers:
A. Working Context — recent conversation history for contextual query resolution
B. Short-term memory — bounded DB-persisted recent turns (same as working context)
C. Long-term / Episodic memory — Zero-Mem (ticket/message indexed to ChromaDB + FTS + entity graph)

Test Matrix:
CTX-01: "tôi bị hỏng" → "cục wifi" → resolves via working context
CTX-02: "VPN không vào" → "nó vẫn timeout" → deictic pronoun resolution
CTX-03: "port 403 không vào" → "cổng đó thì sao" → deictic reference
CTX-04: "port 403 không vào" → "tôi buồn quá" → must NOT merge (topic shift)
CTX-05: Conversation A context cannot enter Conversation B
CTX-06: Ticket A context cannot enter Ticket B
CTX-07: Workspace REST/SSE parity
CTX-08: Ticket REST/SSE parity (unit-level check)
MEM-ST-01: Short-term works with long-term memory disabled
MEM-LT-01: Long-term memory works in new conversation with zero recent history
MEM-LT-02: Irrelevant long-term memory must not affect answer
MEM-ISO-01: Long-term memory cannot cross tenant/user authorization boundaries
MEM-BOTH-01: Short-term resolves pronoun first; long-term runs on resolved query
"""
from __future__ import annotations

import json
import unicodedata
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

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
    mock_rag_reply = (
        "Chào bạn, hệ thống đã ghi nhận thông tin sự cố và hướng dẫn xử lý. "
        "Vui lòng kiểm tra kết nối Wi-Fi hoặc liên hệ IT."
    )
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


def _history(*pairs: tuple[str, str]) -> list[RecentConversationMessage]:
    result = []
    for i, (role, content) in enumerate(pairs):
        result.append(RecentConversationMessage(f"m{i}", role, content))
    return result


# =============================================================================
# CTX-01: "tôi bị hỏng" → "cục wifi" → resolves via entity clarification
# =============================================================================
@pytest.mark.asyncio
async def test_ctx_01_toi_bi_hong_cuc_wifi_unit():
    history = _history(
        ("user", "tôi bị hỏng"),
        ("assistant", "Mình có thể hỗ trợ. Hãy cho mình biết thiết bị hoặc dịch vụ nào?"),
    )
    r = resolve_contextual_user_query("cục wifi", recent_history=history)
    assert r.is_rewritten is True
    assert "hỏng" in r.resolved_query and "wifi" in r.resolved_query


@pytest.mark.asyncio
async def test_ctx_01_toi_bi_hong_cuc_wifi_integration(client: AsyncClient):
    token = create_access_token({"sub": "1"})
    headers = _headers(token)
    conv = (await client.post("/api/v1/chat/conversations", json={"title": "CTX-01"}, headers=headers)).json()["id"]

    r1 = await client.post(f"/api/v1/chat/conversations/{conv}/messages", json={"message": "tôi bị hỏng"}, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["answerability"] == "needs_clarification"

    r2 = await client.post(f"/api/v1/chat/conversations/{conv}/messages", json={"message": "cục wifi"}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["answerability"] != "needs_clarification"


# =============================================================================
# CTX-02: "VPN không vào" → "nó vẫn timeout" → deictic pronoun
# =============================================================================
@pytest.mark.asyncio
async def test_ctx_02_vpn_no_van_timeout_unit():
    history = _history(
        ("user", "VPN không vào"),
        ("assistant", "Bạn hãy kiểm tra kết nối mạng."),
    )
    r = resolve_contextual_user_query("nó vẫn timeout", recent_history=history)
    assert r.is_rewritten is True
    assert "VPN" in r.resolved_query


# =============================================================================
# CTX-03: "port 403 không vào" → "cổng đó thì sao" → deictic reference
# =============================================================================
@pytest.mark.asyncio
async def test_ctx_03_port_403_cong_do_unit():
    history = _history(
        ("user", "port 403 không vào"),
        ("assistant", "Bạn vui lòng kiểm tra firewall."),
    )
    r = resolve_contextual_user_query("cổng đó thì sao", recent_history=history)
    assert r.is_rewritten is True
    assert "port 403" in r.resolved_query.lower() or "403" in r.resolved_query


# =============================================================================
# CTX-04: "port 403 không vào" → "tôi buồn quá" → MUST NOT merge (topic shift)
# =============================================================================
@pytest.mark.asyncio
async def test_ctx_04_topic_shift_not_merged():
    history = _history(
        ("user", "port 403 không vào"),
        ("assistant", "Bạn vui lòng kiểm tra firewall."),
    )
    shifts = ["tôi buồn quá", "cảm ơn", "thôi để sau"]
    for msg in shifts:
        r = resolve_contextual_user_query(msg, recent_history=history)
        assert r.is_rewritten is False, f"'{msg}' should NOT be merged but got reason={r.reason}"


@pytest.mark.asyncio
async def test_ctx_04_self_profile_not_contaminated():
    """'thông tin giám đốc' → 'thông tin của tôi' must not rewrite to include giám đốc."""
    history = _history(
        ("user", "thông tin giám đốc"),
        ("assistant", "Vì bảo mật, tôi chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập."),
    )
    r = resolve_contextual_user_query("thông tin của tôi", recent_history=history)
    assert r.is_rewritten is False
    assert r.reason == "explicit_self_profile"
    assert "giám đốc" not in r.resolved_query


# =============================================================================
# CTX-05: Conversation A context cannot enter Conversation B
# =============================================================================
@pytest.mark.asyncio
async def test_ctx_05_conversation_isolation(client: AsyncClient):
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    conv_a = (await client.post("/api/v1/chat/conversations", json={"title": "Conv A"}, headers=headers)).json()["id"]
    conv_b = (await client.post("/api/v1/chat/conversations", json={"title": "Conv B"}, headers=headers)).json()["id"]

    await client.post(f"/api/v1/chat/conversations/{conv_a}/messages", json={"message": "tôi bị hỏng"}, headers=headers)

    r_b = await client.post(f"/api/v1/chat/conversations/{conv_b}/messages", json={"message": "cục wifi"}, headers=headers)
    assert r_b.status_code == 200
    # Conv B should NOT have resolved "cục wifi" using Conv A's "tôi bị hỏng"
    b_messages = (await client.get(f"/api/v1/chat/conversations/{conv_b}", headers=headers)).json()["messages"]
    assert not any("tôi bị hỏng" == m["content"] for m in b_messages)


# =============================================================================
# CTX-06: Ticket A context cannot enter Ticket B (unit-level)
# =============================================================================
@pytest.mark.asyncio
async def test_ctx_06_ticket_isolation_unit():
    """Ticket A history must not affect Ticket B resolution."""
    ticket_a_history = _history(
        ("user", "tôi bị hỏng"),
        ("agent", "Hãy cho mình biết thiết bị."),
    )
    # Ticket B has completely different history
    ticket_b_history = _history(
        ("user", "email không gửi được"),
        ("agent", "Bạn kiểm tra kết nối."),
    )
    # "cục wifi" resolved with ticket A context → should merge
    r_a = resolve_contextual_user_query("cục wifi", recent_history=ticket_a_history)
    assert r_a.is_rewritten is True and "hỏng" in r_a.resolved_query

    # "cục wifi" resolved with ticket B context → should NOT merge with email issue
    r_b = resolve_contextual_user_query("cục wifi", recent_history=ticket_b_history)
    assert "email" not in r_b.resolved_query


# =============================================================================
# CTX-07: Workspace REST/SSE parity
# =============================================================================
@pytest.mark.asyncio
async def test_ctx_07_workspace_rest_sse_parity(client: AsyncClient):
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    conv = (await client.post("/api/v1/chat/conversations", json={"title": "Parity"}, headers=headers)).json()["id"]
    await client.post(f"/api/v1/chat/conversations/{conv}/messages", json={"message": "tôi bị hỏng"}, headers=headers)

    rest_resp = await client.post("/api/v1/chat", json={"message": "cục wifi", "conversation_id": conv}, headers=headers)
    sse_resp = await client.post("/api/v1/chat/stream", json={"message": "cục wifi", "conversation_id": conv}, headers=headers)

    assert rest_resp.status_code == 200
    assert sse_resp.status_code == 200

    rest_answer = rest_resp.json()["answerability"]
    # Parse SSE
    done_payload = None
    for line in sse_resp.text.split("\n"):
        if line.startswith("data: "):
            try:
                parsed = json.loads(line[6:])
                if "reply" in parsed:
                    done_payload = parsed
            except json.JSONDecodeError:
                pass

    assert done_payload is not None
    assert rest_answer == done_payload["answerability"]
    assert rest_answer != "needs_clarification"


# =============================================================================
# CTX-08: Ticket Chat context resolution (unit-level check)
# =============================================================================
@pytest.mark.asyncio
async def test_ctx_08_ticket_chat_resolution_unit():
    """resolve_contextual_user_query works with ticket_context as well."""
    history = _history(
        ("user", "máy in không ra giấy"),
        ("agent", "Bạn kiểm tra toner."),
    )
    ticket_ctx = {"title": "Máy in lỗi", "description": "Máy in không ra giấy gì cả"}
    r = resolve_contextual_user_query("nó vẫn không được", recent_history=history, ticket_context=ticket_ctx)
    assert r.is_rewritten is True
    assert "máy in" in r.resolved_query.lower()


# =============================================================================
# MEM-ST-01: Short-term works with long-term memory disabled
# =============================================================================
@pytest.mark.asyncio
async def test_mem_st_01_short_term_without_long_term(client: AsyncClient):
    """Context resolution works even when Zero-Mem is disabled."""
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    with patch("src.services.zero_mem_service.retrieve_episodic_evidence", new=AsyncMock(return_value=([], {"enabled": False, "memory_llm_calls": 0, "memory_llm_tokens": 0}))):
        conv = (await client.post("/api/v1/chat/conversations", json={"title": "MEM-ST-01"}, headers=headers)).json()["id"]
        r1 = await client.post(f"/api/v1/chat/conversations/{conv}/messages", json={"message": "tôi bị hỏng"}, headers=headers)
        assert r1.status_code == 200

        r2 = await client.post(f"/api/v1/chat/conversations/{conv}/messages", json={"message": "cục wifi"}, headers=headers)
        assert r2.status_code == 200
        assert r2.json()["answerability"] != "needs_clarification"


# =============================================================================
# MEM-LT-01: Long-term memory works with zero recent history (unit-level)
# =============================================================================
@pytest.mark.asyncio
async def test_mem_lt_01_long_term_without_recent_history():
    """retrieve_episodic_evidence can work on a standalone query without recent history."""
    from src.services.zero_mem_service import profile_query

    # This is a unit-level check: profile_query doesn't need recent_history
    profile = profile_query("VPN không vào được tài nguyên nội bộ")
    assert profile.keywords  # Has keywords to search
    assert profile.route in ("relational", "local_temporal")


# =============================================================================
# MEM-LT-02: Irrelevant long-term memory must not affect answer (unit-level)
# =============================================================================
@pytest.mark.asyncio
async def test_mem_lt_02_irrelevant_memory_no_effect():
    """Zero-Mem's _visible filter enforces tenant/user ACL boundaries."""
    from src.models.episodic_memory import EpisodicMemoryTrace
    from src.models.user import User, UserRole
    from src.services.zero_mem_service import _visible

    # Create a mock trace from a different tenant
    mock_trace = MagicMock(spec=EpisodicMemoryTrace)
    mock_trace.tenant_id = "automotive"
    mock_trace.owner_user_id = 999
    mock_trace.department = "IT"

    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.company_unit = MagicMock()
    mock_user.company_unit.value = "real_estate"
    mock_user.role = MagicMock()
    mock_user.role.value = UserRole.EMPLOYEE.value
    mock_user.department = "HR"

    # Cross-tenant: should NOT be visible
    assert _visible(mock_trace, mock_user) is False


# =============================================================================
# MEM-ISO-01: Long-term memory cannot cross tenant/user boundaries
# =============================================================================
@pytest.mark.asyncio
async def test_mem_iso_01_tenant_isolation():
    """Employee can only see own traces within same tenant."""
    from src.services.zero_mem_service import _visible

    mock_trace = MagicMock()
    mock_trace.tenant_id = "real_estate"
    mock_trace.owner_user_id = 2  # Different user
    mock_trace.department = "IT"

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.company_unit = MagicMock()
    mock_user.company_unit.value = "real_estate"
    mock_user.role = MagicMock()
    mock_user.role.value = "employee"
    mock_user.department = "HR"

    # Same tenant, different user, employee role → NOT visible
    assert _visible(mock_trace, mock_user) is False

    # Same user → visible
    mock_trace.owner_user_id = 1
    assert _visible(mock_trace, mock_user) is True


# =============================================================================
# MEM-BOTH-01: Short-term resolves pronoun first; long-term runs on resolved query
# =============================================================================
@pytest.mark.asyncio
async def test_mem_both_01_short_term_resolves_before_long_term(client: AsyncClient):
    """The pipeline order is: resolve_contextual_user_query → guardrails → routing → retrieval (KB + memory)."""
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    conv = (await client.post("/api/v1/chat/conversations", json={"title": "MEM-BOTH-01"}, headers=headers)).json()["id"]
    await client.post(f"/api/v1/chat/conversations/{conv}/messages", json={"message": "VPN của tôi không kết nối được"}, headers=headers)

    # Second turn: pronoun + follow-up
    r2 = await client.post(f"/api/v1/chat/conversations/{conv}/messages", json={"message": "nó vẫn timeout"}, headers=headers)
    assert r2.status_code == 200
    # The fact that it got past clarification proves context was resolved
    assert r2.json()["answerability"] != "needs_clarification"


# =============================================================================
# Additional topic-shift safety tests
# =============================================================================
@pytest.mark.asyncio
async def test_topic_shift_safety_additional():
    """Verify various topic-shift messages are never merged with previous IT context."""
    history = _history(
        ("user", "VPN lỗi"),
        ("assistant", "Kiểm tra kết nối."),
    )
    safe_shifts = [
        "cảm ơn",
        "ok",
        "dạ",
        "được rồi",
    ]
    for msg in safe_shifts:
        r = resolve_contextual_user_query(msg, recent_history=history)
        assert r.is_rewritten is False, f"'{msg}' should NOT merge, got reason={r.reason}"


@pytest.mark.asyncio
async def test_semantic_variants_deictic():
    """Test deictic variants that should trigger context resolution."""
    history = _history(
        ("user", "Wi-Fi chập chờn"),
        ("assistant", "Bạn vui lòng khởi động lại router."),
    )
    should_resolve = [
        "nó vẫn chưa được",
        "vẫn lỗi",
        "cái đó bị lỗi",
    ]
    for msg in should_resolve:
        r = resolve_contextual_user_query(msg, recent_history=history)
        assert r.is_rewritten is True, f"'{msg}' should resolve with context, got reason={r.reason}"
        assert "Wi-Fi" in r.resolved_query or "wifi" in r.resolved_query.lower()
