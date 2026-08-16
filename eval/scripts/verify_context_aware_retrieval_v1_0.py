import asyncio
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath("."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from src.api.chat import ChatRequest, _chat_with_agent
from src.database import AsyncSessionLocal
from src.models.chat_conversation import ChatConversation, ChatMessage
from src.models.ticket import Ticket
from src.models.ticket_message import TicketMessage, TicketMessageSender
from src.models.user import User
from src.services.context_query_service import (
    build_context_aware_retrieval_query,
    is_context_dependent,
)
from src.services.rag_service import search_similar_async
from src.services.recent_conversation_context import (
    RecentConversationMessage,
    load_ticket_recent_history,
    load_workspace_recent_history,
)
from src.services.ticket_conversation_service import add_message, handle_ticket_message


async def run_evaluation():
    print("=== STARTING CTX-FIX-2 EVALUATION RUNNER ===")
    results = {}

    # ------------------------------------------------------------------------
    # 1. Latency Benchmark
    # ------------------------------------------------------------------------
    print("\n--- 1. LATENCY OVERHEAD BENCHMARK ---")
    benchmark_history = [
        RecentConversationMessage("m1", "user", "Lỗi VPN 809 khi kết nối từ xa trên máy Windows 11."),
        RecentConversationMessage("m2", "assistant", "Bước 1: Mở cổng UDP 500/4500. Bước 2: Khởi động lại IPSec."),
        RecentConversationMessage("m3", "user", "Đã mở cổng rồi."),
        RecentConversationMessage("m4", "assistant", "Hãy kiểm tra registry key AssumeUDPEncapsulationContextOnSendRule."),
    ]
    current_q = "Tôi đã thử bước đầu tiên rồi nhưng vẫn không được."

    times = []
    for _ in range(500):
        t0 = time.perf_counter()
        _ = build_context_aware_retrieval_query(current_q, recent_history=benchmark_history)
        times.append((time.perf_counter() - t0) * 1000)

    avg_latency_ms = sum(times) / len(times)
    p95_latency_ms = sorted(times)[int(len(times) * 0.95)]
    print(f"Latency average: {avg_latency_ms:.4f} ms | p95: {p95_latency_ms:.4f} ms (Target < 2.0 ms)")
    results["latency"] = {
        "avg_ms": round(avg_latency_ms, 4),
        "p95_ms": round(p95_latency_ms, 4),
        "target_ms": 2.0,
        "status": "PASS" if avg_latency_ms < 2.0 else "FAIL",
    }

    # ------------------------------------------------------------------------
    # 2. A/B Retrieval Comparison
    # ------------------------------------------------------------------------
    print("\n--- 2. A/B RETRIEVAL COMPARISON (Raw vs Context-Aware) ---")
    test_cases = [
        {
            "id": "AB-01",
            "topic": "VPN 809",
            "history": [
                RecentConversationMessage("1", "user", "VPN FortiClient báo lỗi 809 trên Windows 11."),
                RecentConversationMessage("2", "assistant", "1. Kiểm tra port UDP 500/4500. 2. Sửa registry."),
            ],
            "current": "Tôi đã thử bước đầu tiên rồi nhưng vẫn không được.",
            "target_keywords": ["vpn", "809", "forticlient", "registry"],
            "expected_kb_tag": "VPN",
        },
        {
            "id": "AB-02",
            "topic": "Outlook Mail",
            "history": [
                RecentConversationMessage("1", "user", "Outlook không gửi được email, thư kẹt trong Outbox."),
                RecentConversationMessage("2", "assistant", "Cách 1: Xóa Outbox offline. Cách 2: Tạo profile mới."),
            ],
            "current": "Tôi thử cách thứ nhất rồi.",
            "target_keywords": ["outlook", "email", "outbox", "profile"],
            "expected_kb_tag": "Outlook",
        },
        {
            "id": "AB-03",
            "topic": "Printer Paper Jam",
            "history": [
                RecentConversationMessage("1", "user", "Máy in Canon LBP 2900 bị kẹt giấy liên tục."),
                RecentConversationMessage("2", "assistant", "1. Mở nắp khay lấy giấy. 2. Vệ sinh con lăn kéo giấy."),
            ],
            "current": "Cách 2 làm thế nào?",
            "target_keywords": ["máy in", "canon", "giấy", "con lăn"],
            "expected_kb_tag": "Printer",
        },
        {
            "id": "AB-04",
            "topic": "WiFi 802.1X",
            "history": [
                RecentConversationMessage("1", "user", "Không kết nối được mạng WiFi VinAI-Staff."),
                RecentConversationMessage("2", "assistant", "Chọn bảo mật WPA2-Enterprise với chứng chỉ nội bộ."),
            ],
            "current": "Vẫn báo Authentication failed.",
            "target_keywords": ["wifi", "vinai-staff", "wpa2", "chứng chỉ"],
            "expected_kb_tag": "Network",
        },
    ]

    ab_results = []
    for tc in test_cases:
        # A: Raw query
        raw_query = tc["current"]
        docs_raw = await search_similar_async(raw_query, n_results=5, user_company_unit="corporate", user_department="IT")
        raw_top_score = float(docs_raw[0].get("relevance_score", 0.0)) if docs_raw else 0.0
        raw_hit = any(any(k in doc.get("content", "").lower() for k in tc["target_keywords"]) for doc in docs_raw)

        # B: Context-aware query
        res_b = build_context_aware_retrieval_query(tc["current"], recent_history=tc["history"])
        docs_ctx = await search_similar_async(res_b.query, n_results=5, user_company_unit="corporate", user_department="IT")
        ctx_top_score = float(docs_ctx[0].get("relevance_score", 0.0)) if docs_ctx else 0.0
        ctx_hit = any(any(k in doc.get("content", "").lower() for k in tc["target_keywords"]) for doc in docs_ctx)

        print(f"Case [{tc['id']}] {tc['topic']}:")
        print(f"  Raw Query: '{raw_query}' -> Top Score: {raw_top_score:.4f} | Relevant Hit: {raw_hit}")
        print(f"  Context Query: '{res_b.query[:80]}...' -> Top Score: {ctx_top_score:.4f} | Relevant Hit: {ctx_hit}")

        ab_results.append({
            "id": tc["id"],
            "topic": tc["topic"],
            "raw_query": raw_query,
            "raw_top_score": raw_top_score,
            "raw_hit": raw_hit,
            "ctx_query": res_b.query,
            "ctx_top_score": ctx_top_score,
            "ctx_hit": ctx_hit,
            "score_delta": round(ctx_top_score - raw_top_score, 4),
        })

    results["ab_comparison"] = ab_results

    # ------------------------------------------------------------------------
    # 3. Real Runtime Verification with Mistral LLM
    # ------------------------------------------------------------------------
    print("\n--- 3. REAL RUNTIME VERIFICATION WITH MISTRAL LLM ---")
    runtime_cases = []

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).order_by(User.id))).scalars().first()

        # Workspace Conversation Case: VPN 809 Follow-up
        print("\n* Running Workspace Runtime Turn 1 & Turn 2...")
        conv = ChatConversation(user_id=user.id, title="VPN Support Session")
        db.add(conv)
        await db.flush()

        msg_1 = ChatMessage(conversation_id=conv.id, role="user", content="VPN FortiClient bị lỗi 809 trên Windows 11.")
        db.add(msg_1)
        await db.commit()

        history_1 = await load_workspace_recent_history(db, conversation_id=conv.id, user_id=user.id, exclude_message_id=msg_1.id)
        resp_1 = await _chat_with_agent(ChatRequest(message=msg_1.content), current_user=user, db=db, recent_history=history_1)
        bot_1 = ChatMessage(conversation_id=conv.id, role="assistant", content=resp_1.reply)
        db.add(bot_1)
        await db.commit()

        # Follow up turn
        msg_2 = ChatMessage(conversation_id=conv.id, role="user", content="Tôi đã thử bước đầu tiên rồi nhưng vẫn không được.")
        db.add(msg_2)
        await db.commit()

        history_2 = await load_workspace_recent_history(db, conversation_id=conv.id, user_id=user.id, exclude_message_id=msg_2.id)
        t_start = time.perf_counter()
        resp_2 = await _chat_with_agent(ChatRequest(message=msg_2.content), current_user=user, db=db, recent_history=history_2)
        turn2_lat_ms = (time.perf_counter() - t_start) * 1000

        print(f"Workspace Turn 2 Reply:\n{resp_2.reply}\n")
        print(f"Workspace Turn 2 Sources: {[s.title for s in resp_2.sources]}")
        print(f"Confidence: {resp_2.confidence} | Retrieval confidence: {resp_2.retrieval_confidence}")

        ws_vpn_pass = bool(resp_2.reply and ("vpn" in resp_2.reply.lower() or "809" in resp_2.reply or "registry" in resp_2.reply.lower() or "ipsec" in resp_2.reply.lower() or len(resp_2.sources) > 0))
        runtime_cases.append({
            "case": "Workspace VPN 809 follow-up",
            "turn_1_query": msg_1.content,
            "turn_2_query": msg_2.content,
            "turn_2_reply_snippet": resp_2.reply[:200],
            "sources": [s.title for s in resp_2.sources],
            "retrieval_confidence": resp_2.retrieval_confidence,
            "confidence": resp_2.confidence,
            "latency_ms": round(turn2_lat_ms, 2),
            "status": "PASS" if ws_vpn_pass else "FAIL",
        })

        # Ticket Conversation Case: Multi-turn follow-up
        print("\n* Running Ticket Conversation Multi-Turn...")
        ticket = Ticket(
            ticket_number="INC-EVAL-RET-01",
            title="Outlook không gửi được email",
            description="Email kẹt trong Outbox, không gửi đi được.",
            submitter_id=user.id,
        )
        db.add(ticket)
        await db.flush()

        # Turn 1
        t_msg_1 = await handle_ticket_message(db, ticket=ticket, user=user, content="Tôi cần hỗ trợ xử lý Outlook không gửi được thư.")
        await db.commit()

        # Turn 2: Context dependent follow up
        t_msg_2 = await handle_ticket_message(db, ticket=ticket, user=user, content="Tôi thử cách thứ nhất rồi.")
        await db.commit()

        last_agent_msg = [m for m in t_msg_2 if m.sender_type == TicketMessageSender.AGENT][-1]
        print(f"Ticket Turn 2 Reply:\n{last_agent_msg.content}\n")
        print(f"Ticket Turn 2 Sources: {last_agent_msg.sources_json}")

        ticket_pass = bool(last_agent_msg.content and ("outlook" in last_agent_msg.content.lower() or "email" in last_agent_msg.content.lower() or "hướng" in last_agent_msg.content.lower() or "bước" in last_agent_msg.content.lower()))
        runtime_cases.append({
            "case": "Ticket Outlook multi-turn follow-up",
            "turn_1_query": "Tôi cần hỗ trợ xử lý Outlook không gửi được thư.",
            "turn_2_query": "Tôi thử cách thứ nhất rồi.",
            "turn_2_reply_snippet": last_agent_msg.content[:200],
            "sources": last_agent_msg.sources_json,
            "status": "PASS" if ticket_pass else "FAIL",
        })

    results["runtime_cases"] = runtime_cases

    # ------------------------------------------------------------------------
    # Save Verification Artifacts
    # ------------------------------------------------------------------------
    with open("eval/results/context_aware_retrieval_v1_0.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n=== EVALUATION FINISHED SUCCESSFULLY ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(run_evaluation())
