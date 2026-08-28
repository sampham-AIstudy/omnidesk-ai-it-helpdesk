"""HITL node — Multi-Factor Risk Engine & Deterministic Policy Engine Integration."""
from __future__ import annotations

import json
import logging

from src.agents.nodes.policy_engine import evaluate_policy
from src.agents.state import TicketAgentState

logger = logging.getLogger(__name__)


def calculate_ticket_risk_score(state: TicketAgentState) -> tuple[float, dict[str, float]]:
    """
    Bộ máy Rủi ro Đa nhân tố (Calibrated 0.0 -> 1.0):
    Risk Score = (priority * 0.20) + (impact * 0.25) + (action_sensitivity * 0.30) + (uncertainty * 0.15) + (privilege * 0.10)

    Thành phần uncertainty sử dụng điểm C_RAG confidence duy nhất:
        uncertainty = 1.0 - confidence   (AI càng tự tin, rủi ro bất định càng thấp)
    """
    # Default 0.5 CHỈ dùng cho tính toán uncertainty trong Risk Score (thành phần nội bộ).
    # Không ảnh hưởng đến policy_engine — policy engine đọc state["confidence_score"] trực tiếp
    # và xử lý None theo logic riêng (Rule 4 / Rule 4b).
    confidence = float(state.get("confidence_score") or 0.5)
    is_production = state.get("is_production_impact", False)
    is_vip = state.get("submitter_is_vip", False)
    category = state.get("category", "other")
    priority = state.get("priority", "medium")
    urgency = state.get("urgency", "medium")
    description = (state.get("description", "") + " " + state.get("title", "")).lower()

    # 1. Priority Score (0.20) — Mức ưu tiên xử lý Ticket
    priority_map = {"low": 0.1, "medium": 0.3, "high": 0.7, "critical": 1.0}
    priority_score = priority_map.get(priority, 0.3)

    # 2. System Impact Score (0.25) — Mức độ thiệt hại nếu không xử lý kịp thời
    impact_score = 1.0 if is_production else (0.8 if urgency == "emergency" else 0.2)

    # 3. Action Sensitivity Score (0.30) — Mức độ nguy hiểm của hành động được yêu cầu
    action_risk_keywords = ["reset password", "admin", "mat khau", "quyen truy cap", "permission", "hardware replacement", "thay the phan cung", "database", "server"]
    has_sensitive_action = any(k in description for k in action_risk_keywords)
    cat_risk_map = {"security": 1.0, "infrastructure": 0.8, "access_permission": 0.9, "erp_sap": 0.7}
    action_score = max(cat_risk_map.get(category, 0.2), 1.0 if has_sensitive_action else 0.1)

    # 4. Uncertainty Score (0.15) — Độ bất định/không chắc chắn của câu trả lời AI
    # AI càng tự tin (confidence cao), uncertainty càng thấp → rủi ro bất định giảm.
    uncertainty_score = max(0.0, 1.0 - confidence)

    # 5. Privilege Risk Score (0.10) — Cấp bậc người gửi yêu cầu
    privilege_score = 1.0 if is_vip else 0.2

    # Tổng hợp trọng số Risk Score
    risk_score = round(
        (priority_score * 0.20) +
        (impact_score * 0.25) +
        (action_score * 0.30) +
        (uncertainty_score * 0.15) +
        (privilege_score * 0.10),
        2
    )

    components = {
        "priority": priority_score,
        "impact": impact_score,
        "action_sensitivity": action_score,
        "uncertainty": uncertainty_score,
        "privilege": privilege_score,
    }

    return risk_score, components


async def hitl_check_node(state: TicketAgentState) -> TicketAgentState:
    """Đánh giá Risk Engine & Deterministic Safety Policy Engine."""
    risk_score, components = calculate_ticket_risk_score(state)
    policy_res = evaluate_policy(state, risk_score)

    # Không có ngữ cảnh RAG → AI không có căn cứ KB để tự trả lời.
    # Tự động chuyển cho Chuyên viên IT hỗ trợ trừ khi Policy Engine đã kích hoạt REQUIRE_HITL.
    if (
        not state.get("rag_context")
        and not state.get("is_production_impact", False)
        and policy_res["decision"] != "REQUIRE_HITL"
    ):
        return {
            **state,
            "hitl_required": False,
            "hitl_reason": "Không có tài liệu KB phù hợp — Chuyển Chuyên viên IT hỗ trợ.",
            "risk_score": risk_score,
            "action_taken": "human_handoff",
            "decision_factors_json": json.dumps({
                "risk_score": risk_score,
                "components": components,
                "policy_decision": "ESCALATE",
                "policy_triggered": "POLICY_NO_RELEVANT_KB_HANDOFF",
                "action_type": "HUMAN_HANDOFF",
                "target_status": "waiting_for_agent",
            }, ensure_ascii=False),
        }

    # Quyết định HITL dựa hoàn toàn vào Policy Engine (đã bao gồm tất cả ngưỡng confidence & risk).
    hitl_required = policy_res["decision"] == "REQUIRE_HITL"
    reason_text = f"[{policy_res['policy_triggered']}] {policy_res['reason']} (Risk: {risk_score:.2f})"

    logger.info(
        f"[PolicyEngine] Ticket #{state.get('ticket_number')} "
        f"Decision: {policy_res['decision']} | Action: {policy_res['action_type']} | "
        f"Confidence: {state.get('confidence_score')} | Risk: {risk_score:.2f}"
    )

    decision_factors = {
        "risk_score": risk_score,
        "components": components,
        "policy_decision": policy_res["decision"],
        "policy_triggered": policy_res["policy_triggered"],
        "action_type": policy_res["action_type"],
        "target_status": policy_res["target_status"],
        "confidence_score": state.get("confidence_score"),
    }

    return {
        **state,
        "hitl_required": hitl_required,
        "hitl_reason": reason_text,
        "risk_score": risk_score,
        "action_taken": policy_res["action_type"].lower(),
        "decision_factors_json": json.dumps(decision_factors, ensure_ascii=False),
    }
