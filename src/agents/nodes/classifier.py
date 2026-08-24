"""Classifier node — Phân loại ticket bằng Mistral LLM với confidence scoring."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import TicketAgentState
from src.config import get_settings
from src.observability.tracing import set_current_attributes, traced_async_operation
from src.services.llm import get_classifier_llm
from src.services.ticket_text import user_report
from src.services.token_cost import dispatch_token_logging

logger = logging.getLogger(__name__)
settings = get_settings()

CLASSIFIER_SYSTEM_PROMPT = """Bạn là AI phân loại ticket IT Help Desk cho tập đoàn lớn.
Nhiệm vụ: Phân tích mô tả ticket và trả về JSON phân loại chính xác.

CATEGORIES:
- network: Mạng, WiFi, VPN, Internet
- software: Phần mềm, ứng dụng, Office, crash
- hardware: Máy tính, máy in, màn hình, thiết bị vật lý
- access_permission: Mật khẩu, quyền truy cập, tài khoản, MFA
- email: Email, Outlook, Exchange
- erp_sap: SAP, ERP, hệ thống kế toán/quản trị
- security: Virus, phishing, bảo mật, rủi ro
- hr_system: HR portal, lương, nghỉ phép
- infrastructure: Server, database, hạ tầng hệ thống
- other: Không thuộc các mục trên

PRIORITY (mức độ ưu tiên xử lý):
- critical: Ảnh hưởng production, nhiều người, hệ thống y tế/tài chính → SLA 1h
- high: Ảnh hưởng công việc của ≥1 người, không thể làm việc → SLA 4h
- medium: Ảnh hưởng một phần, vẫn làm được → SLA 8h
- low: Không khẩn cấp, yêu cầu mới → SLA 24h

URGENCY (mức độ cấp bách của user):
- emergency: Cần xử lý ngay, hệ thống hoàn toàn dừng
- high: Cần trong hôm nay
- medium: Trong vài ngày tới
- low: Khi rảnh

Trả về JSON theo format sau (KHÔNG thêm text ngoài JSON):
{
  "category": "<category_value>",
  "priority": "<priority_value>",
  "urgency": "<urgency_value>",
  "confidence": <0.0-1.0>,
  "reasoning": "<giải thích ngắn gọn tại sao phân loại như vậy>",
  "is_production_impact": <true|false>,
  "suggested_routing_team": "<tên nhóm kỹ thuật phù hợp>"
}"""


@traced_async_operation("ai.route")
async def classify_node(state: TicketAgentState) -> TicketAgentState:
    """Phân loại ticket sử dụng Mistral LLM."""
    logger.info(f"[Classifier] Classifying ticket #{state.get('ticket_number')}")

    llm = get_classifier_llm()
    title = state.get("title", "")
    description = state.get("description", "")
    report_title, report_description = user_report(title, description)
    company = state.get("company_unit", "corporate")
    is_prod = state.get("is_production_impact", False)
    is_vip = state.get("submitter_is_vip", False)

    user_prompt = f"""Phân loại ticket sau:

TIÊU ĐỀ NGƯỜI DÙNG VIẾT: {report_title}
MÔ TẢ NGƯỜI DÙNG VIẾT: {report_description}
CÔNG TY: {company}
PRODUCTION IMPACT (user khai báo): {"Có" if is_prod else "Không"}
NGƯỜI GỬI VIP: {"Có" if is_vip else "Không"}

Trả về JSON phân loại."""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        set_current_attributes({
            "gen_ai.request.model": getattr(llm, "model", getattr(llm, "model_name", "unknown")),
            "helpdesk.ticket.workflow": "classified",
        })

        # --- Theo dõi token & chi phí (chạy nền, không chặn request) ---
        _model_name = str(getattr(llm, "model_name", getattr(llm, "model", "mistral-small-latest")))
        dispatch_token_logging(
            ai_message=response,
            model_name=_model_name,
            user_id=state.get("submitter_id"),
        )

        content = response.content.strip()
        # Xử lý nếu LLM wrap trong ```json ... ```
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)

        # Validate required fields
        category = result.get("category", "other")
        priority = result.get("priority", "medium")
        urgency = result.get("urgency", "medium")
        confidence = float(result.get("confidence", 0.5))
        reasoning = result.get("reasoning", "")
        routing = result.get("suggested_routing_team", "IT General")

        # Tự động nâng priority nếu là production hoặc VIP
        if (is_prod or is_vip) and priority not in ("critical", "high"):
            priority = "high"
            reasoning += " [Auto-upgraded: production impact or VIP submitter]"

        # Tự động set production impact nếu category liên quan hạ tầng
        if category in ("infrastructure", "security") and "production" in description.lower():
            is_prod = True

        logger.info(
            f"[Classifier] ticket={state.get('ticket_number')} "
            f"category={category} priority={priority} confidence={confidence:.2f}"
        )

        from src.services.ai_logger import log_web_app_ai_event
        log_web_app_ai_event(
            event_name="ClassifierAgent",
            prompt=f"Title: {title}\nDescription: {description}",
            response_summary=f"Category: {category}, Priority: {priority}, Confidence: {confidence:.2f}, Reasoning: {reasoning}",
            model=llm.model if hasattr(llm, 'model') else "mistral-large-latest",
            session_id=str(state.get("ticket_number", "INC-UNK")),
        )


        return {
            **state,
            "category": category,
            "priority": priority,
            "urgency": urgency,
            "confidence_score": confidence,
            "agent_reasoning": reasoning,
            "routing_target": routing,
            "is_production_impact": is_prod,
            "model_used": f"mistral:{llm.model}",
            "processing_start": datetime.now(UTC).isoformat(),
            "token_count": getattr(response, "usage_metadata", {}).get("total_tokens", 0),
            "error": None,
        }

    except json.JSONDecodeError as e:
        logger.error(f"[Classifier] JSON parse error: {e}")
        return {
            **state,
            "category": "other",
            "priority": "medium",
            "urgency": "medium",
            "confidence_score": 0.3,
            "agent_reasoning": f"Không thể parse JSON từ LLM: {str(e)}",
            "routing_target": "IT General",
            "model_used": "mistral",
            "error": f"classification_json_error: {str(e)}",
        }
    except Exception as e:
        set_current_attributes({"helpdesk.ticket.workflow": "classifier_fallback"})
        logger.warning(f"[Classifier] LLM call failed ({e}). Falling back to Heuristic Rule Engine.")

        # Heuristic Rule Engine for Offline / Fallback mode
        text = f"{report_title} {report_description}".lower()
        category = "other"
        priority = "medium"
        urgency = "medium"
        routing = "IT General"

        if any(k in text for k in ["access", "permission", "quyền", "login", "đăng nhập", "mật khẩu", "password", "mfa", "auth"]):
            category = "access_permission"
            routing = "Access Management"
        elif any(k in text for k in ["vpn", "wifi", "network", "mạng", "internet", "ping", "router", "ip"]):
            category = "network"
            routing = "Network Team"
        elif any(k in text for k in ["virus", "security", "bảo mật", "phishing", "injection", "soc", "hack", "threat"]):
            category = "security"
            priority = "high"
            routing = "IT Security Team"
        elif any(k in text for k in ["màn hình", "bàn phím", "máy in", "hardware", "laptop", "pc", "cáp"]):
            category = "hardware"
            routing = "Hardware Support"
        elif any(k in text for k in ["sap", "erp", "misa", "office", "excel", "software", "phần mềm", "app"]):
            category = "software"
            routing = "Software Support"

        if "critical" in text or "sập" in text or "khẩn cấp" in text:
            priority = "critical"
            urgency = "high"

        if is_prod or is_vip:
            priority = "high"

        return {
            **state,
            "category": category,
            "priority": priority,
            "urgency": urgency,
            "confidence_score": 0.45,
            "agent_reasoning": "[Heuristic Fallback Engine] Phân loại dựa trên luật từ khóa vì LLM bận/lỗi API key",
            "routing_target": routing,
            "model_used": "rule-heuristic-fallback",
            "error": None,
        }
