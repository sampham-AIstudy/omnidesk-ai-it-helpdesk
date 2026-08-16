"""Evaluation runner for KB-GAP-1 Service Request Process Knowledge Grounding."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from src.api.chat import ChatRequest, _chat_with_agent
from src.data.service_request_kb import SERVICE_REQUEST_KB_ENTRY
from src.database import AsyncSessionLocal
from src.models.chat_conversation import ChatConversation, ChatMessage
from src.models.knowledge_base import KnowledgeBaseEntry
from src.models.user import User
from src.services.chat_routing_service import route_chat_message
from src.services.context_query_service import build_context_aware_retrieval_query
from src.services.rag_service import (
    get_collection,
    get_collection_count,
    index_document,
    search_similar_async,
)
from src.services.recent_conversation_context import (
    RecentConversationMessage,
    load_workspace_recent_history,
)


async def run_evaluation():
    print("=== STARTING KB-GAP-1 SERVICE REQUEST KNOWLEDGE EVALUATION RUNNER ===")
    results = {}

    # Ensure kb-036 is seeded
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.chroma_id == "kb-036")
        )
        entry = res.scalar_one_or_none()
        if entry is None:
            entry = KnowledgeBaseEntry(
                chroma_id="kb-036",
                title=SERVICE_REQUEST_KB_ENTRY["title"],
                content=SERVICE_REQUEST_KB_ENTRY["content"],
                solution=SERVICE_REQUEST_KB_ENTRY.get("solution"),
                runbook=SERVICE_REQUEST_KB_ENTRY.get("runbook"),
                category=SERVICE_REQUEST_KB_ENTRY["category"],
                tags=SERVICE_REQUEST_KB_ENTRY.get("tags"),
                applicable_to_all=True,
                is_active=True,
            )
            db.add(entry)
            await db.commit()

    # Index in Chroma
    content_for_embedding = f"{SERVICE_REQUEST_KB_ENTRY['title']}. {SERVICE_REQUEST_KB_ENTRY['content']}"
    if SERVICE_REQUEST_KB_ENTRY.get("solution"):
        content_for_embedding += f" Giải pháp: {SERVICE_REQUEST_KB_ENTRY['solution']}"
    index_document(
        doc_id="kb-036",
        content=content_for_embedding,
        metadata={
            "title": SERVICE_REQUEST_KB_ENTRY["title"],
            "category": SERVICE_REQUEST_KB_ENTRY["category"],
            "tags": SERVICE_REQUEST_KB_ENTRY.get("tags", ""),
            "solution": SERVICE_REQUEST_KB_ENTRY.get("solution", ""),
            "runbook": SERVICE_REQUEST_KB_ENTRY.get("runbook", ""),
            "company_unit": "all",
            "department": "",
            "applicable_to_all": True,
        },
    )

    results["chroma_stats"] = {
        "collection_name": get_collection().name,
        "total_documents": get_collection_count(),
        "canonical_kb_id": "kb-036",
        "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "dimensions": 384,
    }
    print(f"Chroma Collection: {get_collection().name} | Total docs: {get_collection_count()}")

    # ------------------------------------------------------------------------
    # 1. Retrieval Matrix & A/B Comparison
    # ------------------------------------------------------------------------
    print("\n--- 1. RETRIEVAL MATRIX & GROUNDING EVALUATION ---")
    matrix_cases = [
        {"id": "KB-SR-01", "query": "Service Request là gì?"},
        {"id": "KB-SR-02", "query": "Quy trình Service Request gồm những bước nào?"},
        {"id": "KB-SR-03", "query": "Sau khi gửi Service Request thì ai duyệt?"},
        {"id": "KB-SR-04", "query": "Trạng thái PENDING_APPROVAL nghĩa là gì?"},
        {"id": "KB-SR-05", "query": "Yêu cầu của tôi bị REJECTED nghĩa là sao?"},
        {"id": "KB-SR-06", "query": "Khi nào kỹ thuật viên nhận yêu cầu?"},
        {"id": "KB-SR-07", "query": "WAITING_FOR_USER nghĩa là gì?"},
        {"id": "KB-SR-08", "query": "Service Request khác Incident thế nào?"},
    ]

    retrieval_results = []
    for tc in matrix_cases:
        q = tc["query"]
        route_decision = route_chat_message(q)
        docs = await search_similar_async(q, n_results=5, user_company_unit="corporate", user_department="IT")

        rank = None
        kb36_score = 0.0
        for idx, doc in enumerate(docs):
            if doc.get("doc_id") == "kb-036":
                rank = idx + 1
                kb36_score = float(doc.get("relevance_score", 0.0))
                break

        top_score = float(docs[0].get("relevance_score", 0.0)) if docs else 0.0
        print(f"[{tc['id']}] '{q}' -> Route: {route_decision.route} | kb-036 Rank: {rank} (Top Score: {top_score:.4f}, kb-036 Score: {kb36_score:.4f})")

        retrieval_results.append({
            "id": tc["id"],
            "query": q,
            "route": route_decision.route,
            "kb_retrieved": rank is not None,
            "rank": rank,
            "top_score": round(top_score, 4),
            "kb36_score": round(kb36_score, 4),
            "status": "PASS" if rank is not None and rank <= 5 else "FAIL",
        })

    results["retrieval_matrix"] = retrieval_results

    # ------------------------------------------------------------------------
    # 2. Real Runtime Mistral Grounded Generation
    # ------------------------------------------------------------------------
    print("\n--- 2. REAL RUNTIME MISTRAL GROUNDED GENERATION ---")
    runtime_qa = []
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).order_by(User.id))).scalars().first()

        for tc in [
            {"id": "QA-SR-01", "query": "Service Request là gì?"},
            {"id": "QA-SR-02", "query": "Quy trình Service Request gồm những bước nào?"},
            {"id": "QA-SR-03", "query": "Sau khi gửi Service Request thì ai duyệt?"},
            {"id": "QA-SR-04", "query": "Trạng thái PENDING_APPROVAL nghĩa là gì?"},
            {"id": "QA-SR-08", "query": "Service Request khác Incident thế nào?"},
        ]:
            q = tc["query"]
            t0 = time.perf_counter()
            resp = await _chat_with_agent(ChatRequest(message=q), current_user=user, db=db)
            lat_ms = (time.perf_counter() - t0) * 1000

            sources = [s.title for s in resp.sources]
            print(f"\n* [{tc['id']}] Q: '{q}' (Latency: {lat_ms:.2f} ms)")
            print(f"  Sources: {sources}")
            print(f"  Reply:\n{resp.reply}\n")

            has_source = any("Service Request" in s for s in sources)
            runtime_qa.append({
                "id": tc["id"],
                "query": q,
                "sources": sources,
                "reply_snippet": resp.reply[:250],
                "confidence": resp.confidence,
                "retrieval_confidence": resp.retrieval_confidence,
                "latency_ms": round(lat_ms, 2),
                "grounded": has_source or ("Service Request" in resp.reply or "REQ-" in resp.reply),
            })

        # ------------------------------------------------------------------------
        # 3. Context-Aware Follow-up (CTX-FIX-2 Verification)
        # ------------------------------------------------------------------------
        print("\n--- 3. CONTEXT-AWARE FOLLOW-UP (CTX-FIX-2) ---")
        conv = ChatConversation(user_id=user.id, title="Service Request Process Consultation")
        db.add(conv)
        await db.flush()

        # Turn 1
        t1_msg = ChatMessage(conversation_id=conv.id, role="user", content="Quy trình Service Request gồm những bước nào?")
        db.add(t1_msg)
        await db.commit()

        h1 = await load_workspace_recent_history(db, conversation_id=conv.id, user_id=user.id, exclude_message_id=t1_msg.id)
        resp1 = await _chat_with_agent(ChatRequest(message=t1_msg.content), current_user=user, db=db, recent_history=h1)
        b1_msg = ChatMessage(conversation_id=conv.id, role="assistant", content=resp1.reply)
        db.add(b1_msg)
        await db.commit()

        # Turn 2: Follow-up
        t2_msg = ChatMessage(conversation_id=conv.id, role="user", content="Thế ai là người duyệt?")
        db.add(t2_msg)
        await db.commit()

        h2 = await load_workspace_recent_history(db, conversation_id=conv.id, user_id=user.id, exclude_message_id=t2_msg.id)
        qr = build_context_aware_retrieval_query(t2_msg.content, recent_history=h2)
        resp2 = await _chat_with_agent(ChatRequest(message=t2_msg.content), current_user=user, db=db, recent_history=h2)

        print(f"Turn 1 Query: '{t1_msg.content}'")
        print(f"Turn 2 Follow-up: '{t2_msg.content}'")
        print(f"Turn 2 Rewritten Query: '{qr.query}' (rewritten={qr.rewritten})")
        print(f"Turn 2 Sources: {[s.title for s in resp2.sources]}")
        print(f"Turn 2 Reply:\n{resp2.reply}\n")

        results["context_aware_followup"] = {
            "turn_1": t1_msg.content,
            "turn_2": t2_msg.content,
            "turn_2_rewritten_query": qr.query,
            "turn_2_sources": [s.title for s in resp2.sources],
            "turn_2_reply_snippet": resp2.reply[:250],
            "status": "PASS" if ("Service Request" in qr.query and len(resp2.sources) > 0) else "FAIL",
        }

        # ------------------------------------------------------------------------
        # 4. Action-Grounding Control (C4.1 Verification)
        # ------------------------------------------------------------------------
        print("\n--- 4. ACTION-GROUNDING CONTROL (C4.1) ---")
        act_query = "Tạo Service Request xin laptop cho tôi"
        act_route = route_chat_message(act_query)
        act_resp = await _chat_with_agent(ChatRequest(message=act_query), current_user=user, db=db)

        print(f"Action Query: '{act_query}'")
        print(f"Route: {act_route.route} (should_retrieve={act_route.should_retrieve})")
        print(f"Sources: {[s.title for s in act_resp.sources]}")
        print(f"Reply:\n{act_resp.reply}\n")

        results["action_grounding_control"] = {
            "query": act_query,
            "route": act_route.route,
            "should_retrieve": act_route.should_retrieve,
            "sources_count": len(act_resp.sources),
            "reply_snippet": act_resp.reply[:250],
            "status": "PASS" if act_route.route == "action_request" and len(act_resp.sources) == 0 else "FAIL",
        }

    results["runtime_qa"] = runtime_qa

    with open("eval/results/service_request_knowledge_grounding_v1_0.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n=== EVALUATION FINISHED SUCCESSFULLY ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(run_evaluation())
