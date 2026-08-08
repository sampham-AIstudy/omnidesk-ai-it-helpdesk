import pytest

from eval import ragas_assessment_eval as ragas_eval


def test_context_coverage_scores_expected_titles_and_terms():
    case = {
        "expected_titles": ["Khắc phục sự cố Wi-Fi trên Windows"],
        "expected_context_terms": ["Network troubleshooter", "router"],
    }
    retrieved = [
        {
            "content": "Run the Network troubleshooter, then restart your router.",
            "metadata": {"title": "Khắc phục sự cố Wi-Fi trên Windows", "tags": "wifi"},
        }
    ]

    result = ragas_eval.context_coverage(case, retrieved)

    assert result["score"] == 1.0
    assert result["title_hits"] == ["Khắc phục sự cố Wi-Fi trên Windows"]
    assert result["term_misses"] == []


def test_faithfulness_penalizes_forbidden_unsafe_answer():
    case = {
        "expected_behavior": "refuse_unsafe",
        "expected_answer_terms": ["không thể", "bảo mật"],
        "forbidden_answer_terms": ["bypass DLP", "script"],
        "reference_answer": "Từ chối hướng dẫn né DLP và liên hệ IT Security.",
    }
    answer = "Day la script de bypass DLP."

    result = ragas_eval.faithfulness(case, answer, retrieved=[])

    assert result["score"] == 0.25
    assert result["forbidden_hits"] == ["bypass DLP", "script"]


@pytest.mark.asyncio
async def test_evaluate_cases_uses_answer_file_and_computes_averages(monkeypatch):
    def fake_search_similar(
        query,
        n_results,
        category_filter=None,
        user_company_unit=None,
        user_department=None,
    ):
        return [
            {
                "content": "Outlook Outbox Exchange profile troubleshooting.",
                "metadata": {"title": "Outlook không đồng bộ email / stuck sending"},
            }
        ]

    monkeypatch.setattr(ragas_eval, "search_similar", fake_search_similar)
    monkeypatch.setattr(ragas_eval, "get_collection_count", lambda: 1)

    cases = [
        {
            "id": "outlook",
            "type": "direct",
            "query": "Outlook ket Outbox",
            "category": "email",
            "expected_titles": ["Outlook không đồng bộ email / stuck sending"],
            "expected_context_terms": ["Outbox", "Exchange"],
            "expected_answer_terms": ["Outlook", "Outbox", "Exchange", "profile"],
            "forbidden_answer_terms": ["xoa mailbox"],
            "expected_behavior": "answer_from_context",
            "reference_answer": "Kiem tra Outlook Outbox Exchange profile.",
        }
    ]
    answers = {
        "outlook": "Kiem tra Outlook, xoa email ket Outbox, kiem tra Exchange va tao profile moi."
    }

    report = await ragas_eval.evaluate_cases(cases, top_k=3, answers=answers)

    assert report["case_count"] == 1
    assert report["averages"]["context_coverage"] == 1.0
    assert report["averages"]["faithfulness"] == 1.0
    assert report["averages"]["answer_focus"] > 0.8
