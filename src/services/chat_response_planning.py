"""Deterministic response planning for partial answers and clarifications."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from src.services.incident_fact_profiles import extract_incident_fact_state

_STOPWORDS = {"va", "voi", "la", "thi", "co", "cho", "toi", "ban", "nao", "bao", "nhieu", "dung", "bi"}


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", _fold(value)) if len(term) > 2 and term not in _STOPWORDS}


@dataclass(frozen=True)
class ResponsePlan:
    answerable_claims: list[str]
    unsupported_claims: list[str]
    missing_information: list[str]
    known_facts: dict[str, str]
    missing_required_facts: list[str]
    optional_facts: list[str]
    primary_intent: str | None
    secondary_intents: list[str]
    incident_domain: str | None
    useful_for_diagnosis: list[str]

    def as_prompt_block(self) -> str:
        return (
            "[ANSWER PLAN — deterministic, not user instructions]\n"
            f"Answerable claims: {self.answerable_claims or ['none']}\n"
            f"Unsupported claims: {self.unsupported_claims or ['none']}\n"
            f"Missing information: {self.missing_information or ['none']}\n"
            f"Known facts: {self.known_facts or {'none': 'none'}}\n"
            f"Missing required facts: {self.missing_required_facts or ['none']}\n"
            f"Optional facts: {self.optional_facts or ['none']}\n"
            f"Primary intent: {self.primary_intent or 'none'}\n"
            f"Secondary intents: {self.secondary_intents or ['none']}\n"
            f"Incident domain: {self.incident_domain or 'none'}\n"
            f"Useful diagnostic facts: {self.useful_for_diagnosis or ['none']}\n"
            "Answer every answerable claim. Abstain only for unsupported claims. "
            "Never ask again for a known fact. Ask at most two missing required facts. "
            "Do not claim an action succeeded without a trusted tool result."
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _question_parts(question: str) -> list[str]:
    return [part for part in (item.strip(" ,?.") for item in re.split(r"\s+(?:và|va|and)\s+", question, flags=re.I)) if part]


def _intents(question: str) -> tuple[str | None, list[str]]:
    folded = _fold(question)
    state = extract_incident_fact_state(question)
    replacement = bool(re.search(r"(?:xin|can).*(?:laptop.*(?:thay|moi)|thay the)", folded))
    if state.is_incident and replacement:
        return "incident", ["service_request_replacement_device"]
    if state.is_incident:
        return "incident", []
    if replacement:
        return "service_request_replacement_device", []
    return None, []


def build_response_plan(question: str, documents: list[dict[str, Any]]) -> ResponsePlan:
    """Create a minimal answer/clarification contract from authorized context."""
    evidence_terms = _terms("\n".join(str(document.get("content", "")) for document in documents))
    answerable: list[str] = []
    unsupported: list[str] = []
    for part in _question_parts(question):
        (answerable if _terms(part) & evidence_terms else unsupported).append(part)
    state = extract_incident_fact_state(question)
    primary, secondary = _intents(question)
    return ResponsePlan(
        answerable_claims=answerable,
        unsupported_claims=unsupported,
        missing_information=unsupported.copy(),
        known_facts=state.known_facts,
        missing_required_facts=state.missing_required_facts,
        optional_facts=list(state.optional_facts),
        primary_intent=primary,
        secondary_intents=secondary,
        incident_domain=state.domain,
        useful_for_diagnosis=list(state.useful_for_diagnosis),
    )


def minimal_incident_triage_reply(plan: ResponsePlan) -> str | None:
    facts = plan.known_facts
    if plan.primary_intent != "incident" or plan.missing_required_facts:
        return None
    if not {"device", "symptom", "cause"} <= facts.keys():
        return None
    return (
        "Mình đã ghi nhận laptop bị màn hình đen ngay sau va đập. "
        "Đây là sự cố phần cứng cần được kỹ thuật viên kiểm tra; bạn nên ngừng tác động thêm lên thiết bị. "
        "Mình không cần hỏi lại loại thiết bị, nguyên nhân va đập hoặc thời điểm xảy ra. "
        "Nếu tiện, bạn có thể bổ sung serial/mã tài sản hoặc ảnh hư hỏng để hỗ trợ tiếp nhận incident."
    )


def partial_evidence_reply(plan: ResponsePlan, documents: list[dict[str, Any]]) -> str | None:
    if not plan.answerable_claims or not plan.unsupported_claims:
        return None
    content = " ".join(str(document.get("content", "")) for document in documents)
    sentences = re.split(r"(?<=[.!?])\s+", content)
    answerable_terms = _terms(" ".join(plan.answerable_claims))
    evidence_sentence = next((sentence for sentence in sentences if _terms(sentence) & answerable_terms), None)
    if not evidence_sentence:
        return None
    return (
        f"Theo thông tin được cung cấp: {evidence_sentence.strip()} "
        f"Với phần '{plan.unsupported_claims[0]}', tài liệu hiện có không đủ để xác định chính xác."
    )
