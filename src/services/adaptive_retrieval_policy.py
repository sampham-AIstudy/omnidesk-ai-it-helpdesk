"""Small deterministic policy around the existing hybrid retriever.

This module owns only post-retrieval evidence sufficiency, one bounded retry,
and adaptive evidence count.  It never ranks candidates, changes ACLs, or
persists user query text.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from src.config import get_settings
from src.services.query_normalization_service import normalize_informal_query
from src.services.technical_intent_service import infer_technical_facets

RetrievalOutcome = Literal["STRONG", "ADEQUATE", "WEAK", "EMPTY"]
AsyncRetriever = Callable[[str], Awaitable[list[dict]]]
MAX_INTERNAL_RETRIES_PER_USER_TURN = 1
# Keep the retry deterministic and narrow: a technical facet may contribute no
# more than two additional concepts to the existing resolved query.
MAX_RETRY_EXPANSION_TERMS = 2


@dataclass(frozen=True)
class AdaptiveRetrievalResult:
    """In-memory result; telemetry deliberately excludes raw/retry queries."""

    documents: list[dict]
    outcome: RetrievalOutcome
    retrieval_passes: int
    retry_triggered: bool
    retry_reason: str | None
    retry_improved: bool

    def telemetry(self) -> dict[str, str | int | bool | None]:
        return {
            "retrieval_outcome": self.outcome,
            "retrieval_pass": self.retrieval_passes,
            "retry_triggered": self.retry_triggered,
            "retry_reason": self.retry_reason,
            "retry_improved": self.retry_improved,
            "final_evidence_count": len(self.documents),
        }


@dataclass(frozen=True)
class AdaptiveTurnResult:
    """A single user turn's retrieval results and globally bounded telemetry."""

    results: list[AdaptiveRetrievalResult]
    subquery_count: int
    initial_search_count: int
    retry_search_count: int

    def telemetry(self) -> dict[str, str | int | bool | None]:
        retry_result = next((result for result in self.results if result.retry_triggered), None)
        final_outcome = next(
            (result.outcome for result in self.results if result.outcome in {"WEAK", "EMPTY"}),
            self.results[0].outcome if self.results else "EMPTY",
        )
        return {
            "subquery_count": self.subquery_count,
            "initial_search_count": self.initial_search_count,
            "retry_search_count": self.retry_search_count,
            "turn_retry_budget": MAX_INTERNAL_RETRIES_PER_USER_TURN,
            "retry_budget_consumed": self.retry_search_count,
            "retry_reason": retry_result.retry_reason if retry_result else None,
            "retry_improved": retry_result.retry_improved if retry_result else False,
            "final_outcome": final_outcome,
            "final_evidence_count": sum(len(result.documents) for result in self.results),
        }


def _score(document: dict) -> float:
    return float(document.get("relevance_score", 0.0) or 0.0)


def _agrees(document: dict) -> bool:
    return document.get("dense_rank") is not None and document.get("lexical_rank") is not None


def _technical_support(document: dict) -> bool:
    return float(document.get("exact_contribution", 0.0) or 0.0) > 0 or float(
        document.get("topic_compatibility", 1.0) or 1.0
    ) > 1.0


def classify_retrieval_outcome(documents: list[dict]) -> RetrievalOutcome:
    """Classify existing hybrid evidence without an LLM or new score floors.

    ``rag_min_relevance_score`` remains the only score floor.  Agreement is
    needed because calibrated top scores may otherwise be .75 for a single
    weak channel.  Exact/technical support permits a high-confidence fast path.
    """
    if not documents:
        return "EMPTY"
    top = documents[0]
    if _score(top) < get_settings().rag_min_relevance_score:
        return "WEAK"
    # Legacy/unit-test evidence may predate hybrid provenance.  Preserve its
    # established score-based handling instead of treating absent fields as a
    # negative signal; only a one-channel result is weak evidence.
    if top.get("dense_rank") is None and top.get("lexical_rank") is None:
        return "ADEQUATE"
    if _agrees(top) and _technical_support(top):
        return "STRONG"
    floor = get_settings().rag_min_relevance_score
    if _agrees(top) and max(float(top.get("semantic_score", 0.0) or 0.0), float(top.get("lexical_score", 0.0) or 0.0)) >= floor:
        return "ADEQUATE"
    return "WEAK"


_FACET_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "network.tcp_connectivity": ("TCP connectivity", "service listening", "firewall"),
    "network.port_connectivity": ("TCP connectivity", "service listening", "firewall"),
    "network.port_timeout": ("routing", "firewall"),
    "network.connection_refused": ("service listening", "firewall allow rule"),
    "network.service_not_listening": ("service listening", "firewall allow rule"),
    "vpn.internal_resource_access": ("routing", "split tunnel", "internal DNS"),
    "vpn.forticlient_auth": ("authentication", "certificate", "VPN profile"),
    "dns": ("DNS resolution", "Resolve-DnsName"),
    "routing": ("routing", "split tunnel"),
    "proxy": ("proxy", "proxy authentication"),
    # This deliberately remains application semantics; it never adds TCP port.
    "http.status_403": ("HTTP authorization", "application access"),
}


def build_bounded_retry_query(query: str) -> str:
    """Append at most ``MAX_RETRY_EXPANSION_TERMS`` facet-proven concepts."""
    normalized = normalize_informal_query(query).strip()
    facets = infer_technical_facets(normalized)
    additions = _FACET_EXPANSIONS.get(facets.predicted_topic, ())[:MAX_RETRY_EXPANSION_TERMS]
    present = normalized.casefold()
    bounded = [term for term in additions if term.casefold() not in present]
    return " ".join([normalized, *bounded]).strip()[:400]


def _canonical_key(document: dict) -> str:
    metadata = document.get("metadata") or {}
    return str(metadata.get("canonical_source_id") or document.get("doc_id") or metadata.get("source_id") or "")


def merge_retry_documents(first_pass: list[dict], second_pass: list[dict]) -> list[dict]:
    """Deduplicate by chunk and canonical source, preserving stronger evidence."""
    selected: dict[str, dict] = {}
    for document in [*first_pass, *second_pass]:
        chunk_id = str(document.get("doc_id") or "")
        canonical = _canonical_key(document)
        key = canonical or chunk_id
        if not key:
            continue
        existing = selected.get(key)
        if existing is None or _score(document) > _score(existing):
            selected[key] = document
    return sorted(selected.values(), key=lambda item: (-_score(item), str(item.get("doc_id") or "")))


def _select_evidence(documents: list[dict], outcome: RetrievalOutcome) -> list[dict]:
    # One strongly agreed, technically supported anchor is sufficient.  Other
    # classifications preserve the caller's current bounded evidence count.
    return documents[:1] if outcome == "STRONG" else documents


async def retrieve_with_bounded_retry(query: str, retrieve: AsyncRetriever) -> AdaptiveRetrievalResult:
    """Convenience wrapper: one query still uses the shared turn budget."""
    return (await retrieve_turn_with_bounded_retry([query], retrieve)).results[0]


async def retrieve_turn_with_bounded_retry(queries: list[str], retrieve: AsyncRetriever) -> AdaptiveTurnResult:
    """Retrieve all subqueries, then spend at most one retry for the user turn."""
    first_passes = await asyncio.gather(*(retrieve(query) for query in queries))
    outcomes = [classify_retrieval_outcome(documents) for documents in first_passes]
    results = [
        AdaptiveRetrievalResult(
            documents=_select_evidence(documents, outcome), outcome=outcome,
            retrieval_passes=1, retry_triggered=False, retry_reason=None, retry_improved=False,
        )
        for documents, outcome in zip(first_passes, outcomes)
    ]
    retry_index = next((index for index, outcome in enumerate(outcomes) if outcome in {"WEAK", "EMPTY"}), None)
    if retry_index is not None:
        first_outcome = outcomes[retry_index]
        second_pass = await retrieve(build_bounded_retry_query(queries[retry_index]))
        merged = merge_retry_documents(first_passes[retry_index], second_pass)
        final_outcome = classify_retrieval_outcome(merged)
        results[retry_index] = AdaptiveRetrievalResult(
            documents=_select_evidence(merged, final_outcome), outcome=final_outcome,
            retrieval_passes=2, retry_triggered=True,
            retry_reason="empty_internal_evidence" if first_outcome == "EMPTY" else "weak_internal_evidence",
            retry_improved=final_outcome in {"STRONG", "ADEQUATE"},
        )
    return AdaptiveTurnResult(
        results=results,
        subquery_count=len(queries),
        initial_search_count=len(queries),
        retry_search_count=1 if retry_index is not None else 0,
    )
