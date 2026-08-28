"""
Bộ máy Quy tắc An toàn Xác định (Deterministic Safety Policy Engine).
Thực thi các quy tắc nghiệp vụ & an ninh CỨNG sau khi Risk Score AI được tính.
Các quy tắc Hard Policy có quyền GIAO ĐÈ tuyệt đối lên điểm rủi ro LLM.

Ma trận quyết định theo thứ tự ưu tiên:
  1. Danh mục Security / Hành vi nhạy cảm / Sự cố Production → ESCALATE (Chuyển thẳng KTV)
  2. Confidence < 0.45 → ESCALATE (Chuyển ngay Chuyên viên IT)
  3. Confidence >= 0.85 → AUTO_PROCEED resolved (Tự động đóng Ticket)
  4. [Dải bình thường 0.45–0.85] Risk Score >= 0.65 → ESCALATE (Rủi ro cao → KTV xử lý)
  5. [Dải bình thường 0.45–0.85] Risk Score < 0.65 → AUTO_PROCEED pending_closure (Luồng bình thường)

Lưu ý: HITL (Human-In-The-Loop với Manager phê duyệt) đã được bỏ.
Các ticket rủi ro cao được route thẳng đến Chuyên viên IT (ESCALATE / HUMAN_HANDOFF).
"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.state import TicketAgentState

logger = logging.getLogger(__name__)


def evaluate_policy(state: TicketAgentState, risk_score: float) -> dict[str, Any]:
    """
    Bộ máy Quy tắc An toàn Xác định (Ma trận Chính sách An toàn):
    1. Security Category                 → ESCALATE (KTV bảo mật)
    2. Hành vi nhạy cảm / Reset Pass     → ESCALATE (KTV có quyền hệ thống)
    3. Sự cố ảnh hưởng Production        → ESCALATE (KTV hạ tầng)
    4. Confidence C_RAG < 0.45          → ESCALATE (Chuyên viên IT)
    5. Confidence C_RAG >= 0.85         → AUTO_PROCEED (Tự động đóng Ticket)
    6. [0.45 <= C_RAG < 0.85] Risk >= 0.65 → ESCALATE (Rủi ro tổng hợp cao)
    7. [0.45 <= C_RAG < 0.85] Risk < 0.65 → AUTO_PROCEED (Luồng bình thường)
    """
    category = state.get("category", "other")
    is_production = state.get("is_production_impact", False)
    confidence_val = state.get("confidence_score")
    # Nếu không có C_RAG (chat thông thường, không RAG), bỏ qua các Rule confidence.
    confidence: float | None = float(confidence_val) if confidence_val is not None else None
    description = (state.get("description", "") + " " + state.get("title", "")).lower()

    # ── Rule 1: Danh mục Security / Sự cố An ninh ─────────────────────────────
    # Route thẳng đến IT Security Team — KTV bảo mật xử lý trực tiếp.
    if category == "security":
        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_HANDOFF",
            "target_status": "waiting_for_agent",
            "policy_triggered": "POLICY_SECURITY_CATEGORY_ESCALATE",
            "reason": "Ticket thuộc danh mục Security — Chuyển thẳng IT Security Team xử lý",
        }

    # ── Rule 2: Hành vi Nhạy cảm (Reset Password Admin, Phân quyền, Database) ─
    # Route đến KTV có quyền hệ thống — tránh AI tự thực thi hành động nguy hiểm.
    sensitive_keywords = ["reset password", "admin", "quyen root", "sharepoint permission", "database", "drop table"]
    if any(kw in description for kw in sensitive_keywords):
        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_HANDOFF",
            "target_status": "waiting_for_agent",
            "policy_triggered": "POLICY_SENSITIVE_ACTION_ESCALATE",
            "reason": "Yêu cầu chứa hành vi nhạy cảm (Reset password/Phân quyền/Hạ tầng) — Chuyển KTV",
        }

    # ── Rule 3: Sự cố ảnh hưởng hệ thống Production ───────────────────────────
    if is_production:
        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_HANDOFF",
            "target_status": "waiting_for_agent",
            "policy_triggered": "POLICY_PRODUCTION_IMPACT_ESCALATE",
            "reason": "Sự cố ảnh hưởng hệ thống Production — Chuyển KTV hạ tầng xử lý",
        }

    # ── Rules 4 & 5: Phân luồng theo Chỉ số C_RAG Confidence & Ngữ cảnh KB ─────
    no_kb_context = not state.get("rag_context")

    # Rule 4: C_RAG Confidence rất thấp (< 0.45) HOẶC Không tìm thấy KB phù hợp → Chuyển ngay Chuyên viên IT
    # AI không đủ tin cậy để tự trả lời, tự động Escalate sang Chuyên viên IT hỗ trợ.
    if (confidence is not None and confidence < 0.45) or no_kb_context:
        reason_msg = (
            "Không tìm thấy tài liệu Knowledge Base phù hợp — Chuyển Chuyên viên IT hỗ trợ"
            if no_kb_context
            else f"Độ tin cậy RAG quá thấp ({confidence:.2f} < 0.45) — Chuyển Chuyên viên IT hỗ trợ"
        )
        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_HANDOFF",
            "target_status": "waiting_for_agent",
            "policy_triggered": "POLICY_NO_KB_FOUND_ESCALATE" if no_kb_context else "POLICY_LOW_CONFIDENCE_ESCALATE",
            "reason": reason_msg,
        }

    if confidence is not None:
        # Rule 5: C_RAG Confidence cao (>= 0.85) → Trả lời tự động & Đóng Ticket
        # Câu trả lời AI được đánh giá đủ tin cậy để tự động giải quyết Ticket.
        if confidence >= 0.85:
            return {
                "decision": "AUTO_PROCEED",
                "action_type": "AUTO_ANSWER",
                "target_status": "resolved",
                "policy_triggered": "POLICY_HIGH_CONFIDENCE_AUTO_CLOSE",
                "reason": f"Độ tin cậy RAG cao ({confidence:.2f} >= 0.85) — Tự động đóng Ticket",
            }

        # Dải bình thường: 0.45 <= confidence < 0.85
        # Trong dải này, kiểm tra thêm Risk Score tổng hợp để quyết định có cần KTV không.

    # ── Rule 6: Risk Score tổng hợp cao (>= 0.65) → Chuyển KTV xử lý ──────────
    # Áp dụng cho Dải bình thường (0.45–0.85) hoặc khi Chat thường (confidence = None).
    if risk_score >= 0.65:
        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_HANDOFF",
            "target_status": "waiting_for_agent",
            "policy_triggered": "POLICY_HIGH_RISK_SCORE_ESCALATE",
            "reason": f"Điểm rủi ro tổng hợp cao ({risk_score:.2f} >= 0.65) — Chuyển KTV",
        }

    # ── Rule Mặc định: Cho phép luồng bình thường ─────────────────────────────
    return {
        "decision": "AUTO_PROCEED",
        "action_type": "AUTO_ANSWER",
        "target_status": "pending_closure",
        "policy_triggered": "POLICY_DEFAULT_AUTO_PROCEED",
        "reason": "Ticket đạt toàn bộ tiêu chuẩn an toàn tự động",
    }
