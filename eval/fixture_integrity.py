"""Referential-integrity checks for frozen generation fixtures.

An ``EVAL_FIXTURE_ERROR`` is a setup failure, never a generator failure.  This
module is intentionally deterministic and executes before any LLM call.
"""
from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Any


class EvidenceMode(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    NO_EVIDENCE_REQUIRED = "NO_EVIDENCE_REQUIRED"


_NO_EVIDENCE_TYPES = {
    "small_talk", "user_anger_emotion", "rapid_followup", "out_of_scope_garbage",
    "prompt_injection_rag_security", "hacking_dual_use", "memory_privacy",
    "tool_authorization", "access_security", "ticket_operations", "human_escalation",
    "bad_tool_confirmation", "status_accuracy", "minimum_clarification", "over_questioning",
    "ambiguous_incident", "multi_intent", "confidence_ui", "retrieval_hygiene",
}
_UNSUPPORTED_TYPES = {"no_answer_context", "correct_abstention"}
_SUPPORTED_TYPES = {
    "knowledge_query", "network_vpn", "incident_software", "account_password",
    "conflicting_context", "multi_part", "refusal_error", "citation_correctness",
    "search_source_quality", "internet_search_policy", "source_relevance", "duplicate_sources",
}


def expected_evidence_mode(case: dict[str, Any]) -> EvidenceMode:
    kind = case.get("type", "")
    if kind == "partial_context":
        return EvidenceMode.PARTIALLY_SUPPORTED
    if kind in _UNSUPPORTED_TYPES:
        return EvidenceMode.UNSUPPORTED
    if kind in _NO_EVIDENCE_TYPES:
        return EvidenceMode.NO_EVIDENCE_REQUIRED
    if kind in _SUPPORTED_TYPES:
        return EvidenceMode.SUPPORTED
    return EvidenceMode.NO_EVIDENCE_REQUIRED


def _content(context: list[dict[str, Any]]) -> str:
    return "\n".join(str(source.get("content", "")) for source in context).casefold()


def validate_case_fixture(
    case: dict[str, Any], context: list[dict[str, Any]], *, mode: EvidenceMode | None = None,
    requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = mode or expected_evidence_mode(case)
    source_ids = [str(source.get("doc_id") or source.get("metadata", {}).get("source_id") or "") for source in context]
    errors: list[str] = []
    if mode == EvidenceMode.SUPPORTED and not context:
        errors.append("SUPPORTED_CONTEXT_MISSING")
    if mode == EvidenceMode.PARTIALLY_SUPPORTED and not context:
        errors.append("PARTIAL_CONTEXT_MISSING")
    if mode == EvidenceMode.UNSUPPORTED and context:
        errors.append("UNSUPPORTED_CONTEXT_PRESENT")
    content = _content(context)
    requirements = requirements or {}
    if mode == EvidenceMode.PARTIALLY_SUPPORTED:
        if any(term.casefold() not in content for term in requirements.get("required_supported_terms", [])):
            errors.append("PARTIAL_SUPPORTED_EVIDENCE_MISSING")
        if any(term.casefold() in content for term in requirements.get("forbidden_unsupported_terms", [])):
            errors.append("PARTIAL_UNSUPPORTED_ANSWER_LEAK")
    if mode == EvidenceMode.UNSUPPORTED and any(term.casefold() in content for term in requirements.get("forbidden_unsupported_terms", [])):
        errors.append("UNSUPPORTED_ANSWER_LEAK")
    return {
        "id": case["id"], "expected_evidence_mode": mode.value,
        "context_source_ids": source_ids, "integrity": "PASS" if not errors else "EVAL_FIXTURE_ERROR",
        "errors": errors,
    }


def audit_fixture_integrity(
    cases: list[dict[str, Any]], contexts: dict[str, list[dict[str, Any]]], *,
    mode_overrides: dict[str, EvidenceMode] | None = None, requirements: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    mode_overrides, requirements = mode_overrides or {}, requirements or {}
    rows = [validate_case_fixture(case, contexts.get(case["id"], []), mode=mode_overrides.get(case["id"]), requirements=requirements.get(case["id"])) for case in cases]
    failures = [row for row in rows if row["integrity"] != "PASS"]
    return {
        "total": len(rows), "passed": len(rows) - len(failures), "eval_fixture_error_count": len(failures),
        "error_count_by_type": dict(Counter(error for row in failures for error in row["errors"])),
        "cases": rows,
    }
