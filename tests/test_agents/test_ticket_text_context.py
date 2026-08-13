from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.nodes.classifier import classify_node
from src.agents.nodes.rag_node import rag_node
from src.services.ticket_text import user_report
from src.services.web_research_service import ResearchResult, ResearchSource

FORM_DESCRIPTION = """[Hệ Thống / Dịch Vụ: SAP ERP]
[Phân Loại Dịch Vụ: Yêu cầu dịch vụ]
--- MÔ TẢ CHI TIẾT SỰ CỐ ---
làm sao để cài Adobe Creative Cloud"""


def test_user_report_removes_only_known_form_framing():
    title, description = user_report("[SAP ERP] Không biết cài phần mềm", FORM_DESCRIPTION)

    assert title == "Không biết cài phần mềm"
    assert description == "làm sao để cài Adobe Creative Cloud"


@pytest.mark.asyncio
async def test_classifier_uses_free_text_not_form_product_label():
    response = MagicMock()
    response.content = (
        '{"category":"software","priority":"low","urgency":"low",'
        '"confidence":0.9,"reasoning":"software install",'
        '"is_production_impact":false,"suggested_routing_team":"Software Support"}'
    )
    llm = AsyncMock()
    llm.model = "test-model"
    llm.ainvoke = AsyncMock(return_value=response)

    with patch("src.agents.nodes.classifier.get_classifier_llm", return_value=llm):
        result = await classify_node({
            "ticket_number": "INC-TEST-FORM-CONTEXT",
            "title": "[SAP ERP] Không biết cài phần mềm",
            "description": FORM_DESCRIPTION,
            "company_unit": "real_estate",
            "is_production_impact": False,
            "submitter_is_vip": False,
        })

    classifier_prompt = llm.ainvoke.await_args.args[0][1].content
    assert "[SAP ERP]" not in classifier_prompt
    assert "làm sao để cài Adobe Creative Cloud" in classifier_prompt
    assert result["category"] == "software"


@pytest.mark.asyncio
async def test_missing_installation_kb_abstains_without_undocumented_steps():
    with (
        patch("src.agents.nodes.rag_node.search_similar", return_value=[]) as search,
        patch("src.agents.nodes.rag_node.maybe_research_web", AsyncMock(return_value=ResearchResult(False, "provider_unavailable", None, []))),
    ):
        result = await rag_node({
            "ticket_number": "INC-TEST-INSTALL",
            "title": "[SAP ERP] Không biết cài phần mềm",
            "description": FORM_DESCRIPTION,
            "category": "software",
            "company_unit": "real_estate",
            "department": "Sales",
        })

    query = search.call_args.kwargs["query"]
    assert "[SAP ERP]" not in query
    assert "Adobe Creative Cloud" in query
    assert result["suggested_solution"] == "Rất tiếc, thông tin hiện có chưa đủ để trả lời câu hỏi này."
    assert result["rag_context"] == []


@pytest.mark.asyncio
async def test_specific_product_uses_safe_web_research_in_initial_ticket_reply():
    source = ResearchSource(
        title="Adobe Creative Cloud installation", url="https://helpx.adobe.com/creative-cloud/help/download-install.html",
        domain="helpx.adobe.com", snippet="Install Creative Cloud using the official desktop app.",
        content="Install Creative Cloud using the official desktop app.", retrieved_at=datetime.now(UTC),
        source_type="OFFICIAL", relevance_score=0.91,
    )
    response = MagicMock()
    response.content = "Cài bằng ứng dụng Adobe Creative Cloud chính thức, sau đó đăng nhập bằng tài khoản đã được cấp."
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=response)

    with (
        patch("src.agents.nodes.rag_node.search_similar", return_value=[]),
        patch("src.agents.nodes.rag_node.maybe_research_web", AsyncMock(return_value=ResearchResult(True, "internal_kb_empty", "Adobe Creative Cloud", [source]))),
        patch("src.agents.nodes.rag_node.get_rag_llm", return_value=llm),
    ):
        result = await rag_node({
            "ticket_number": "INC-TEST-WEB-INITIAL",
            "title": "Cần cài Adobe Creative Cloud",
            "description": "Không thấy ứng dụng Adobe Creative Cloud trên máy Windows 11.",
            "category": "software",
        })

    assert "Adobe Creative Cloud" in result["suggested_solution"]
    assert result["rag_context"] == []
    assert result["rag_sources"] == [{
        "label": "Adobe Creative Cloud installation",
        "kind": "web",
        "url": "https://helpx.adobe.com/creative-cloud/help/download-install.html",
    }]
