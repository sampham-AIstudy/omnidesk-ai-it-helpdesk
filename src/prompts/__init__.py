"""Versioned, security-critical prompts used by the Help Desk AI."""

from src.prompts.helpdesk_rag import (
    LLM_AS_JUDGE_SYSTEM_PROMPT,
    PRODUCTION_RAG_SYSTEM_PROMPT,
    QUERY_DECOMPOSITION_SYSTEM_PROMPT,
    build_authorized_evidence,
    build_judge_input,
    evidence_source_ids,
    remove_unrecognized_source_ids,
)

__all__ = [
    "LLM_AS_JUDGE_SYSTEM_PROMPT",
    "PRODUCTION_RAG_SYSTEM_PROMPT",
    "QUERY_DECOMPOSITION_SYSTEM_PROMPT",
    "build_authorized_evidence",
    "build_judge_input",
    "evidence_source_ids",
    "remove_unrecognized_source_ids",
]
