"""Post-ranking, metadata-gated parent/neighbor evidence expansion.

This module deliberately does not participate in retrieval, RRF, authority, or
ACL ranking.  It receives already ranked anchors and may only append bounded
context that can be proved to belong to an anchor's canonical source.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from src.config import get_settings
from src.services.rag_service import (
    _metadata_allowed,
    get_collection,
    scan_indirect_injection,
)

_ELIGIBLE_SOURCES = {"internal_curated_kb", "official_web_documentation"}
_PROCEDURAL_KINDS = {"procedure", "procedural", "runbook", "troubleshooting"}
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{1,}", re.IGNORECASE)


@dataclass(frozen=True)
class ExpansionMetrics:
    anchor_count: int
    expanded_neighbor_count: int
    expanded_parent_count: int
    dropped_neighbor_count: int
    anchor_tokens: int
    neighbor_tokens: int
    parent_tokens: int

    @property
    def total_evidence_tokens(self) -> int:
        return self.anchor_tokens + self.neighbor_tokens + self.parent_tokens

    @property
    def expansion_used(self) -> bool:
        return bool(self.expanded_neighbor_count or self.expanded_parent_count)


def _estimate_tokens(value: str) -> int:
    """Stable conservative token estimate; no model/tokenizer call is required."""
    return max(1, (len(value or "") + 3) // 4) if value else 0


def _metadata(document: dict[str, Any]) -> dict[str, Any]:
    return dict(document.get("metadata") or {})


def _explicit_canonical_source(metadata: dict[str, Any]) -> str:
    """Expansion requires a persisted canonical source ID, never a guessed one."""
    value = metadata.get("canonical_source_id")
    return str(value).strip() if value is not None else ""


def _source_kind(metadata: dict[str, Any]) -> str:
    return str(metadata.get("source") or metadata.get("source_type") or "").strip()


def _is_procedural(metadata: dict[str, Any]) -> bool:
    kind = str(metadata.get("document_type") or metadata.get("content_type") or "").casefold()
    return bool(metadata.get("expansion_eligible") is True or kind in _PROCEDURAL_KINDS)


def _has_ordered_document(metadata: dict[str, Any]) -> bool:
    index = metadata.get("chunk_index")
    total = metadata.get("total_chunks")
    try:
        return int(index) >= 0 and int(total) > 1 and int(index) < int(total)
    except (TypeError, ValueError):
        return False


def _same_authorization_scope(anchor: dict[str, Any], candidate: dict[str, Any], *, company_unit: str | None, department: str | None) -> bool:
    anchor_meta, candidate_meta = _metadata(anchor), _metadata(candidate)
    if not _metadata_allowed(candidate_meta, company_unit, department):
        return False
    # If tenant IDs exist, require both and require exact equality.  The same
    # policy applies to an explicitly scoped department; this prevents a
    # neighbor from widening an otherwise authorized anchor's scope.
    anchor_tenant = anchor_meta.get("tenant_id")
    candidate_tenant = candidate_meta.get("tenant_id")
    if anchor_tenant or candidate_tenant:
        if not anchor_tenant or not candidate_tenant or str(anchor_tenant) != str(candidate_tenant):
            return False
    anchor_department = str(anchor_meta.get("department") or "")
    candidate_department = str(candidate_meta.get("department") or "")
    if anchor_department != candidate_department:
        return False
    anchor_company = str(anchor_meta.get("company_unit") or "all")
    candidate_company = str(candidate_meta.get("company_unit") or "all")
    return anchor_company == candidate_company


def _same_section_or_parent(anchor: dict[str, Any], candidate: dict[str, Any]) -> bool:
    anchor_meta, candidate_meta = _metadata(anchor), _metadata(candidate)
    anchor_section = anchor_meta.get("section_id") or anchor_meta.get("section")
    candidate_section = candidate_meta.get("section_id") or candidate_meta.get("section")
    anchor_parent, candidate_parent = anchor_meta.get("parent_document_id"), candidate_meta.get("parent_document_id")
    # Never cross a document boundary, even where an accidentally identical
    # section label appears in two different documents.
    if anchor_parent or candidate_parent:
        if not (anchor_parent and candidate_parent and str(anchor_parent) == str(candidate_parent)):
            return False
    if anchor_section or candidate_section:
        return bool(anchor_section and candidate_section and str(anchor_section) == str(candidate_section))
    return bool(anchor_parent and candidate_parent)


def _same_document_identity(anchor: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """Require a persisted, matching document ID; never infer it from order."""
    anchor_id = str(_metadata(anchor).get("document_id") or "").strip()
    candidate_id = str(_metadata(candidate).get("document_id") or "").strip()
    return bool(anchor_id and candidate_id and anchor_id == candidate_id)


def _unique_chunk_indexes(records: Iterable[dict[str, Any]]) -> set[tuple[str, int]]:
    """Return only explicit document/index pairs that occur exactly once."""
    counts: dict[tuple[str, int], int] = {}
    seen_record_ids: set[str] = set()
    for record in records:
        metadata = _metadata(record)
        record_id = str(record.get("doc_id") or metadata.get("source_id") or "").strip()
        if not record_id or record_id in seen_record_ids:
            continue
        seen_record_ids.add(record_id)
        document_id = str(metadata.get("document_id") or "").strip()
        try:
            index = int(metadata.get("chunk_index"))
        except (TypeError, ValueError):
            continue
        if document_id:
            key = (document_id, index)
            counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count == 1}


def _lexical_related(query: str, anchor: dict[str, Any], candidate: dict[str, Any]) -> bool:
    anchor_meta, candidate_meta = _metadata(anchor), _metadata(candidate)
    anchor_topic, candidate_topic = anchor_meta.get("topic"), candidate_meta.get("topic")
    if anchor_topic and candidate_topic and str(anchor_topic) == str(candidate_topic):
        return True
    query_terms = set(_TOKEN_RE.findall(query.casefold()))
    anchor_terms = set(_TOKEN_RE.findall((str(anchor_meta.get("title") or "") + " " + str(anchor.get("content") or "")).casefold()))
    candidate_terms = set(_TOKEN_RE.findall((str(candidate_meta.get("title") or "") + " " + str(candidate.get("content") or "")).casefold()))
    return bool(candidate_terms & (query_terms | anchor_terms))


def _content_key(document: dict[str, Any]) -> str:
    metadata = _metadata(document)
    return str(metadata.get("content_hash") or re.sub(r"\s+", " ", str(document.get("content") or "")).strip().casefold())


def _anchor_record(anchor: dict[str, Any]) -> dict[str, Any]:
    result = dict(anchor)
    metadata = _metadata(anchor)
    metadata["evidence_role"] = "anchor"
    metadata["citation_source_id"] = str(anchor.get("doc_id") or metadata.get("source_id") or "")
    result["metadata"] = metadata
    return result


def _expanded_record(anchor: dict[str, Any], candidate: dict[str, Any], *, reason: str, relative_position: int) -> dict[str, Any]:
    result = dict(candidate)
    anchor_meta, metadata = _metadata(anchor), _metadata(candidate)
    anchor_id = str(anchor.get("doc_id") or anchor_meta.get("source_id") or "")
    metadata.update({
        "evidence_role": "neighbor",
        "anchor_chunk_id": anchor_id,
        "expanded_chunk_id": str(candidate.get("doc_id") or metadata.get("source_id") or ""),
        "relative_position": relative_position,
        "expansion_reason": reason,
        "citation_source_id": anchor_id,
        "canonical_source_id": _explicit_canonical_source(anchor_meta),
    })
    result["metadata"] = metadata
    # Keep post-ranking application filters from removing an accepted context
    # row; this is not a retrieval score and cannot alter the anchor ranking.
    result["relevance_score"] = anchor.get("relevance_score", 0.0)
    return result


def _parent_record(anchor: dict[str, Any], *, max_chars: int) -> dict[str, Any] | None:
    metadata = _metadata(anchor)
    parent = str(metadata.get("parent_summary") or metadata.get("parent_title") or metadata.get("heading") or "").strip()
    if not parent or not metadata.get("parent_document_id"):
        return None
    anchor_id = str(anchor.get("doc_id") or metadata.get("source_id") or "")
    parent_metadata = dict(metadata)
    # A parent label is not the same content as its anchor chunk.
    parent_metadata.pop("content_hash", None)
    parent_metadata.update({
        "evidence_role": "parent",
        "anchor_chunk_id": anchor_id,
        "expanded_chunk_id": f"{anchor_id}:parent",
        "relative_position": 0,
        "expansion_reason": "bounded_parent_context",
        "citation_source_id": anchor_id,
    })
    return {
        "doc_id": f"{anchor_id}:parent",
        "content": parent[:max_chars],
        "metadata": parent_metadata,
        "relevance_score": anchor.get("relevance_score", 0.0),
    }


def expand_ranked_anchors_from_records(
    query: str,
    anchors: list[dict[str, Any]],
    records: Iterable[dict[str, Any]],
    *,
    company_unit: str | None = None,
    department: str | None = None,
) -> tuple[list[dict[str, Any]], ExpansionMetrics]:
    """Append only proven, bounded context to already-ranked anchor records.

    ``records`` is intentionally supplied separately, which keeps this logic
    testable and makes it impossible to call it from the ranking loop.
    """
    settings = get_settings()
    marked_anchors = [_anchor_record(anchor) for anchor in anchors]
    anchor_tokens = sum(_estimate_tokens(str(item.get("content") or "")) for item in marked_anchors)
    if not settings.context_expansion_enabled or not anchors:
        return marked_anchors, ExpansionMetrics(len(anchors), 0, 0, 0, anchor_tokens, 0, 0)

    candidates = list(records)
    unique_indexes = _unique_chunk_indexes(candidates)
    expanded: list[dict[str, Any]] = []
    used_ids = {str(item.get("doc_id") or "") for item in anchors}
    used_content = {_content_key(item) for item in anchors}
    total_budget = settings.context_expansion_max_evidence_tokens
    remaining = max(0, total_budget - anchor_tokens)
    neighbor_tokens = parent_tokens = dropped = 0
    parent_count = neighbor_count = 0

    for anchor in anchors:
        anchor_meta = _metadata(anchor)
        canonical_id = _explicit_canonical_source(anchor_meta)
        if (
            not canonical_id
            or _source_kind(anchor_meta) not in _ELIGIBLE_SOURCES
            or not _is_procedural(anchor_meta)
            or not _has_ordered_document(anchor_meta)
        ):
            continue
        try:
            anchor_index = int(anchor_meta["chunk_index"])
        except (KeyError, TypeError, ValueError):
            continue

        parent = _parent_record(anchor, max_chars=settings.context_expansion_parent_max_chars)
        if parent is not None and parent_count < settings.context_expansion_max_parent_items:
            tokens = _estimate_tokens(str(parent["content"]))
            if tokens <= remaining and _content_key(parent) not in used_content:
                expanded.append(parent)
                used_ids.add(str(parent["doc_id"]))
                used_content.add(_content_key(parent))
                remaining -= tokens
                parent_tokens += tokens
                parent_count += 1

        per_anchor = 0
        ordered = sorted(candidates, key=lambda item: str(item.get("doc_id") or ""))
        for candidate in ordered:
            candidate_meta = _metadata(candidate)
            candidate_id = str(candidate.get("doc_id") or candidate_meta.get("source_id") or "")
            try:
                relative = int(candidate_meta.get("chunk_index")) - anchor_index
            except (TypeError, ValueError):
                dropped += 1
                continue
            if relative not in (-1, 1):
                continue
            valid = (
                candidate_id not in used_ids
                and _same_document_identity(anchor, candidate)
                and (str(candidate_meta.get("document_id") or "").strip(), int(candidate_meta.get("chunk_index"))) in unique_indexes
                and _explicit_canonical_source(candidate_meta) == canonical_id
                and _source_kind(candidate_meta) == _source_kind(anchor_meta)
                and _has_ordered_document(candidate_meta)
                and _same_authorization_scope(anchor, candidate, company_unit=company_unit, department=department)
                and _same_section_or_parent(anchor, candidate)
                and _lexical_related(query, anchor, candidate)
                and not scan_indirect_injection(str(candidate.get("content") or ""))
                and _content_key(candidate) not in used_content
            )
            if not valid:
                dropped += 1
                continue
            tokens = _estimate_tokens(str(candidate.get("content") or ""))
            if per_anchor >= settings.context_expansion_max_chunks_per_anchor or neighbor_count >= settings.context_expansion_max_total_chunks or tokens > remaining:
                dropped += 1
                continue
            expanded.append(_expanded_record(anchor, candidate, reason="adjacent_ordered_chunk", relative_position=relative))
            used_ids.add(candidate_id)
            used_content.add(_content_key(candidate))
            remaining -= tokens
            neighbor_tokens += tokens
            neighbor_count += 1
            per_anchor += 1

    return marked_anchors + expanded, ExpansionMetrics(
        len(anchors), neighbor_count, parent_count, dropped,
        anchor_tokens, neighbor_tokens, parent_tokens,
    )


def expand_ranked_anchors(
    query: str,
    anchors: list[dict[str, Any]],
    *,
    company_unit: str | None = None,
    department: str | None = None,
) -> tuple[list[dict[str, Any]], ExpansionMetrics]:
    """Load candidates only for persisted canonical IDs, then expand safely."""
    canonical_ids = sorted({_explicit_canonical_source(_metadata(anchor)) for anchor in anchors} - {""})
    records: list[dict[str, Any]] = []
    if canonical_ids:
        collection = get_collection()
        for canonical_id in canonical_ids:
            try:
                result = collection.get(where={"canonical_source_id": canonical_id}, include=["documents", "metadatas"])
            except Exception:
                continue
            records.extend(
                {"doc_id": str(doc_id), "content": content or "", "metadata": metadata or {}}
                for doc_id, content, metadata in zip(result.get("ids", []), result.get("documents", []), result.get("metadatas", []))
            )
    return expand_ranked_anchors_from_records(
        query, anchors, records, company_unit=company_unit, department=department,
    )
