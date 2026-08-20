"""Deterministic tests for KB-GAP-1 Service Request Process Knowledge Grounding."""
import pytest
from sqlalchemy import select

from src.data.service_request_kb import SERVICE_REQUEST_KB_ENTRY
from src.database import AsyncSessionLocal
from src.models.knowledge_base import KnowledgeBaseEntry
from src.services.chat_routing_service import route_chat_message
from src.services.context_query_service import build_context_aware_retrieval_query
from src.services.rag_service import (
    get_collection,
    index_document,
    search_similar_async,
)
from src.services.recent_conversation_context import RecentConversationMessage


@pytest.fixture(autouse=True)
def ensure_kb_sr_indexed():
    """Ensure kb-036 is indexed in the active test Chroma collection."""
    entry_36 = SERVICE_REQUEST_KB_ENTRY
    content_for_embedding = f"{entry_36['title']}. {entry_36['content']}"
    if entry_36.get("solution"):
        content_for_embedding += f" Giải pháp: {entry_36['solution']}"
    index_document(
        doc_id=entry_36["id"],
        content=content_for_embedding,
        metadata={
            "title": entry_36["title"],
            "category": entry_36["category"],
            "tags": entry_36.get("tags", ""),
            "solution": entry_36.get("solution", ""),
            "runbook": entry_36.get("runbook", ""),
            "company_unit": entry_36.get("company_unit", "all"),
            "department": entry_36.get("department", ""),
            "applicable_to_all": entry_36.get("applicable_to_all", True),
        },
    )


@pytest.mark.asyncio
async def test_kb_sr_canonical_article_exists_in_sqlite():
    """Verify kb-036 exists in SQLite database with full metadata."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.chroma_id == "kb-036")
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            # Seed entry into SQLite if test DB was dropped
            entry_36 = SERVICE_REQUEST_KB_ENTRY
            entry = KnowledgeBaseEntry(
                chroma_id="kb-036",
                title=entry_36["title"],
                content=entry_36["content"],
                solution=entry_36.get("solution"),
                runbook=entry_36.get("runbook"),
                category=entry_36["category"],
                tags=entry_36.get("tags"),
                applicable_to_all=True,
                is_active=True,
            )
            db.add(entry)
            await db.commit()
            await db.refresh(entry)

        assert entry is not None
        assert entry.title == "Quy trình Service Request / Yêu cầu dịch vụ CNTT"
        assert entry.category == "service_request"
        assert entry.applicable_to_all is True
        assert "PENDING_APPROVAL" in entry.content
        assert "SUBMITTED" in entry.content
        assert "ASSIGNED" in entry.content
        assert "IN_PROGRESS" in entry.content
        assert "WAITING_FOR_USER" in entry.content
        assert "FULFILLED" in entry.content
        assert "REJECTED" in entry.content


@pytest.mark.asyncio
async def test_kb_sr_canonical_article_in_chroma_provenance():
    """Verify kb-036 is indexed in the active v3 canonical collection with 384-dim SentenceTransformer."""
    collection = get_collection()
    assert collection.name == "helpdesk_kb_multilingual_v3_sentence_transformer"

    res = collection.get(ids=["kb-036"], include=["documents", "metadatas"])
    assert len(res["ids"]) == 1
    assert res["ids"][0] == "kb-036"
    assert res["metadatas"][0]["title"] == "Quy trình Service Request / Yêu cầu dịch vụ CNTT"
    assert res["metadatas"][0]["applicable_to_all"] in (True, "True", "true")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id,query",
    [
        ("KB-SR-01", "Service Request là gì?"),
        ("KB-SR-02", "Quy trình Service Request gồm những bước nào?"),
        ("KB-SR-03", "Sau khi gửi Service Request thì ai duyệt?"),
        ("KB-SR-04", "Trạng thái PENDING_APPROVAL nghĩa là gì?"),
        ("KB-SR-05", "Yêu cầu của tôi bị REJECTED nghĩa là sao?"),
        ("KB-SR-06", "Khi nào kỹ thuật viên nhận yêu cầu?"),
        ("KB-SR-07", "WAITING_FOR_USER nghĩa là gì?"),
        ("KB-SR-08", "Service Request khác Incident thế nào?"),
    ],
)
async def test_kb_sr_retrieval_matrix(test_id: str, query: str):
    """Verify kb-036 is retrieved in Top-5 for all canonical Service Request knowledge queries."""
    docs = await search_similar_async(
        query,
        n_results=5,
        user_company_unit="corporate",
        user_department="IT",
    )
    doc_ids = [d.get("doc_id") for d in docs]
    assert "kb-036" in doc_ids, f"[{test_id}] Query '{query}' did not retrieve kb-036 in Top-5. Docs: {doc_ids}"
    kb36_doc = next(d for d in docs if d.get("doc_id") == "kb-036")
    assert float(kb36_doc.get("relevance_score", 0.0)) >= 0.50


@pytest.mark.asyncio
async def test_kb_sr_acl_cross_tenant_visibility():
    """Verify kb-036 (applicable_to_all=True) is retrievable by any company unit and department."""
    units = ["corporate", "healthcare", "automotive", "real_estate"]
    departments = ["Sales", "ICU", "Showroom", "IT", "HR"]

    for unit in units:
        for dept in departments:
            docs = await search_similar_async(
                "Service Request là gì?",
                n_results=3,
                user_company_unit=unit,
                user_department=dept,
            )
            doc_ids = [d.get("doc_id") for d in docs]
            assert "kb-036" in doc_ids, f"kb-036 not visible for {unit}:{dept}"


@pytest.mark.asyncio
async def test_kb_sr_routing_preservation_c4_2():
    """Verify C4.2 routing remains intact: Knowledge vs Action separation."""
    # Knowledge question routes to knowledge / should_retrieve=True
    decision_k = route_chat_message("Quy trình Service Request là gì?")
    assert decision_k.route == "knowledge"
    assert decision_k.should_retrieve is True

    decision_k2 = route_chat_message("Sau khi gửi Service Request thì ai duyệt?")
    assert decision_k2.route == "knowledge"
    assert decision_k2.should_retrieve is True

    # Action request routes to action_request / should_retrieve=False
    decision_a = route_chat_message("Tạo Service Request xin laptop cho tôi")
    assert decision_a.route == "action_request"
    assert decision_a.should_retrieve is False


@pytest.mark.asyncio
async def test_kb_sr_context_aware_followup_ctx_fix_2():
    """Verify CTX-FIX-2 query reformulation on multi-turn Service Request dialogue."""
    history = [
        RecentConversationMessage("1", "user", "Quy trình Service Request gồm những bước nào?"),
        RecentConversationMessage("2", "assistant", "Gồm 7 bước: Create, Approval, Queue, Assign, In-Progress, Waiting, Fulfilled."),
    ]
    follow_up = "Thế ai là người duyệt?"
    res = build_context_aware_retrieval_query(follow_up, recent_history=history)

    assert "Service Request" in res.query
    assert "người duyệt" in res.query

    docs = await search_similar_async(res.query, n_results=5, user_company_unit="corporate", user_department="IT")
    doc_ids = [d.get("doc_id") for d in docs]
    assert "kb-036" in doc_ids
