"""Deterministic In-Memory Knowledge Graph Retriever for Help Desk AI.

Constructs an in-memory entity/topic/source adjacency graph from canonical Chroma
knowledge base documents. Enables sub-millisecond graph candidate lookup and
deterministic fusion with Dense + BM25 retrieval without external graph databases
or additional LLM calls.
"""
from __future__ import annotations

import logging
import re
import threading
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from src.services.rag_service import (
    SOURCE_AUTHORITY_FACTORS,
    _metadata_allowed,
    get_collection,
    scan_indirect_injection,
)
from src.services.technical_intent_service import TechnicalFacets, infer_technical_facets

logger = logging.getLogger(__name__)

_graph_lock = threading.Lock()
_cached_knowledge_graph: KnowledgeGraphIndex | None = None


def _normalize(text: str) -> str:
    """Normalize text for consistent graph entity matching."""
    norm = unicodedata.normalize("NFKD", text).casefold()
    return "".join(ch for ch in norm if not unicodedata.combining(ch)).replace("đ", "d")


# Entity & Topic extraction patterns for graph linking
GRAPH_ENTITY_PATTERNS: dict[str, list[str]] = {
    "vpn": [
        "vpn", "forticlient", "ssl-vpn", "ssl vpn", "cisco anyconnect",
        "openvpn", "wireguard", "vpn tunnel", "tunnel establishment"
    ],
    "dns": [
        "dns", "resolve-dnsname", "nslookup", "flushdns", "name resolution",
        "dns cache", "dns server", "domain name", "hosts file"
    ],
    "tcp_l4": [
        "tcp", "udp", "port 443", "port 80", "port 22", "port 3389", "port 53",
        "port 8080", "test-netconnection", "tcptestsucceeded", "port connection"
    ],
    "ping_l3": [
        "ping", "icmp", "packet loss", "ping timeout", "echo request"
    ],
    "http_error": [
        "401", "403", "404", "500", "502", "503", "forbidden",
        "unauthorized", "bad gateway", "internal server error", "http status"
    ],
    "wifi": [
        "wifi", "wi-fi", "wireless", "wpa2", "wpa3", "802.1x", "ssid",
        "captive portal", "access point", "roaming", "wifi network"
    ],
    "bitlocker": [
        "bitlocker", "recovery key", "tpm", "drive encryption",
        "unlock drive", "intune bitlocker", "azure ad bitlocker"
    ],
    "m365_outlook": [
        "outlook", "exchange", "office 365", "m365", "ost", "pst",
        "stuck outbox", "outbox", "teams", "onedrive", "sharepoint"
    ],
    "firewall_routing": [
        "firewall", "routing", "gateway", "proxy", "pac file",
        "packet filter", "nat", "subnet", "ip address"
    ],
    "bsod_crash": [
        "bsod", "blue screen", "man hinh xanh", "stop code",
        "dump file", "minidump", "memory management crash"
    ],
    "dlp_security": [
        "dlp", "data loss prevention", "security policy", "exfiltration",
        "usb block", "external drive blocked", "compliance"
    ],
}


@dataclass(frozen=True)
class GraphCandidate:
    doc_id: str
    content: str
    metadata: dict[str, Any]
    matched_entities: tuple[str, ...]
    matched_topics: tuple[str, ...]
    graph_degree: int
    graph_score: float


class KnowledgeGraphIndex:
    """In-memory topic, entity, and canonical source adjacency graph."""

    def __init__(
        self,
        doc_ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        self.doc_ids = doc_ids
        self.documents = {doc_id: doc for doc_id, doc in zip(doc_ids, documents)}
        self.metadatas = {doc_id: meta for doc_id, meta in zip(doc_ids, metadatas)}

        # Adjacency maps
        self.entity_to_docs: dict[str, set[str]] = defaultdict(set)
        self.topic_to_docs: dict[str, set[str]] = defaultdict(set)
        self.category_to_docs: dict[str, set[str]] = defaultdict(set)
        self.doc_to_entities: dict[str, set[str]] = defaultdict(set)
        self.doc_to_topics: dict[str, set[str]] = defaultdict(set)

        self._build_graph()

    def _build_graph(self) -> None:
        """Construct deterministic edges between topics, entities, and documents."""
        for doc_id, meta in self.metadatas.items():
            doc_content = self.documents.get(doc_id, "")
            title = _normalize(str(meta.get("title", "")))
            tags = _normalize(str(meta.get("tags", "")))
            category = _normalize(str(meta.get("category", "")))
            searchable = f"{title} {tags} {category} {_normalize(doc_content)}"

            # Index category edge
            if category:
                self.category_to_docs[category].add(doc_id)

            # Match entities & topics from patterns
            for topic_name, patterns in GRAPH_ENTITY_PATTERNS.items():
                for pat in patterns:
                    norm_pat = _normalize(pat)
                    # Check exact whole-word regex or substring
                    if re.search(rf"\b{re.escape(norm_pat)}\b", searchable):
                        self.entity_to_docs[norm_pat].add(doc_id)
                        self.topic_to_docs[topic_name].add(doc_id)
                        self.doc_to_entities[doc_id].add(norm_pat)
                        self.doc_to_topics[doc_id].add(topic_name)

    def query_graph(
        self,
        query: str,
        technical_facets: TechnicalFacets | None = None,
        user_company_unit: str | None = None,
        user_department: str | None = None,
        max_candidates: int = 15,
    ) -> list[GraphCandidate]:
        """Traverse 1-hop knowledge graph with strict pre-retrieval ACL filtering."""
        norm_query = _normalize(query)
        facets = technical_facets or infer_technical_facets(query)

        # 1. Identify active query entities and topics
        active_entities: set[str] = set()
        active_topics: set[str] = set()

        for topic_name, patterns in GRAPH_ENTITY_PATTERNS.items():
            for pat in patterns:
                norm_pat = _normalize(pat)
                if re.search(rf"\b{re.escape(norm_pat)}\b", norm_query):
                    active_entities.add(norm_pat)
                    active_topics.add(topic_name)

        # Inject facets if determined
        if facets.protocol in {"http", "https"} and facets.http_status:
            active_entities.add(str(facets.http_status))
            active_topics.add("http_error")
        if facets.protocol in {"tcp", "udp"} and facets.port:
            active_entities.add(f"port {facets.port}")
            active_topics.add("tcp_l4")
        if facets.vpn_stage != "unknown":
            active_topics.add("vpn")
            active_entities.add("vpn")

        if not active_entities and not active_topics:
            return []

        # 2. Collect candidate documents via adjacency map
        candidate_match_counts: dict[str, int] = defaultdict(int)
        candidate_matched_entities: dict[str, set[str]] = defaultdict(set)
        candidate_matched_topics: dict[str, set[str]] = defaultdict(set)

        for ent in active_entities:
            for doc_id in self.entity_to_docs.get(ent, ()):
                candidate_match_counts[doc_id] += 2  # Higher weight for specific entity
                candidate_matched_entities[doc_id].add(ent)

        for top in active_topics:
            for doc_id in self.topic_to_docs.get(top, ()):
                candidate_match_counts[doc_id] += 1
                candidate_matched_topics[doc_id].add(top)

        # 3. Filter by ACL & Security Invariants, compute Graph Score
        candidates: list[GraphCandidate] = []
        for doc_id, score in candidate_match_counts.items():
            meta = self.metadatas.get(doc_id, {})
            if not _metadata_allowed(meta, user_company_unit, user_department):
                continue
            doc_content = self.documents.get(doc_id, "")
            if scan_indirect_injection(doc_content):
                continue

            source_type = meta.get("source", "NO_SOURCE_KEY")
            auth_factor = SOURCE_AUTHORITY_FACTORS.get(source_type, 1.0)
            graph_score = score * auth_factor

            candidates.append(
                GraphCandidate(
                    doc_id=doc_id,
                    content=doc_content,
                    metadata=meta,
                    matched_entities=tuple(sorted(candidate_matched_entities[doc_id])),
                    matched_topics=tuple(sorted(candidate_matched_topics[doc_id])),
                    graph_degree=score,
                    graph_score=graph_score,
                )
            )

        # Sort deterministically by graph_score descending, then doc_id
        candidates.sort(key=lambda c: (-c.graph_score, c.doc_id))
        return candidates[:max_candidates]


def get_knowledge_graph_index() -> KnowledgeGraphIndex:
    """Thread-safe singleton factory for KnowledgeGraphIndex."""
    global _cached_knowledge_graph
    if _cached_knowledge_graph is None:
        with _graph_lock:
            if _cached_knowledge_graph is None:
                collection = get_collection()
                data = collection.get(include=["documents", "metadatas"])
                doc_ids = [str(i) for i in data.get("ids", [])]
                documents = data.get("documents", [])
                metadatas = data.get("metadatas", [])
                _cached_knowledge_graph = KnowledgeGraphIndex(
                    doc_ids=doc_ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                logger.info(
                    "Built KnowledgeGraphIndex with %d docs, %d unique entities indexed",
                    len(doc_ids),
                    len(_cached_knowledge_graph.entity_to_docs),
                )
    return _cached_knowledge_graph


def invalidate_knowledge_graph_cache() -> None:
    """Invalidate graph index when underlying KB updates."""
    global _cached_knowledge_graph
    with _graph_lock:
        _cached_knowledge_graph = None
