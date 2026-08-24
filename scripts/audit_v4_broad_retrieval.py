# ruff: noqa: E402, I001
"""Diagnostic-only source-level audit for the V4 broad retrieval benchmark.

This script deliberately does not alter collection contents or retrieval runtime
behaviour.  It exposes the current A3 channels and scoring stages so candidate
recall can be separated from final ranking quality.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(".").resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.services.bm25_retriever as bm25  # noqa: E402
import src.services.rag_service as rag  # noqa: E402
from eval.v4_eval_matching import (
    doc_canonical_aliases,
    doc_matches_targets,
    targets_canonical_aliases,
)  # noqa: E402
from src.services.query_normalization_service import (
    extract_exact_technical_tokens,
    normalize_informal_query,
)  # noqa: E402
from src.services.technical_intent_service import infer_technical_facets, topic_compatibility  # noqa: E402


V3 = "helpdesk_kb_multilingual_v3_sentence_transformer"
V4 = "helpdesk_kb_multilingual_v4_shadow"
DATASET_PATH = Path("eval/broad_coverage_v4.json")
OUT_PATH = Path("eval/results/v4_broad_retrieval_audit.json")
CASE_ID_PATTERN = re.compile(r"^COV-\d{3}$")


def _set_collection(name: str) -> Any:
    collection = rag.get_chroma_client().get_collection(name)
    rag._collection = collection
    rag._rag_query_cache.clear()
    bm25._cached_bm25_index = None
    return collection


def _as_doc(doc_id: str, content: str, metadata: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"doc_id": str(doc_id), "content": str(content or ""), "metadata": metadata or {}, **extra}


def _stage_matches(docs: list[dict[str, Any]], aliases: set[str]) -> bool:
    return any(doc_matches_targets(doc, aliases) for doc in docs)


def _stage_rank(docs: list[dict[str, Any]], aliases: set[str]) -> int | None:
    return next((index + 1 for index, doc in enumerate(docs) if doc_matches_targets(doc, aliases)), None)


def _dense_docs_from_response(raw: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for index, content in enumerate((raw.get("documents") or [[]])[0]):
        meta = ((raw.get("metadatas") or [[]])[0][index]) or {}
        if not rag._metadata_allowed(meta) or rag.scan_indirect_injection(content):
            continue
        doc_id = str((raw.get("ids") or [[]])[0][index])
        distance = float((raw.get("distances") or [[]])[0][index])
        docs.append(_as_doc(
            doc_id, content, meta, distance=distance, semantic_score=max(0.0, 1.0 - distance),
            dense_rank=len(docs) + 1,
        ))
    return docs


def _build_trace(query: str, n_results: int = 5) -> dict[str, Any]:
    """Reconstruct A3's observable stages without modifying A3 itself."""
    collection = rag.get_collection()
    norm_query = normalize_informal_query(query)
    exact_tokens = extract_exact_technical_tokens(query) | extract_exact_technical_tokens(norm_query)
    facets = infer_technical_facets(norm_query)
    expanded_query = rag._expand_query(norm_query if norm_query != query else query)
    dense_limit = min(max(n_results * 8, n_results), collection.count() or 1)
    raw = collection.query(
        query_embeddings=[rag.embed_query(expanded_query)],
        n_results=dense_limit,
        include=["documents", "metadatas", "distances"],
    )
    dense_stage = _dense_docs_from_response(raw)
    dense_docs: dict[str, dict[str, Any]] = {doc["doc_id"]: doc for doc in dense_stage}
    # Probe only: A3 currently consumes 40 dense chunks for top-5, but the
    # requested @50 channel-recall measure needs the raw dense channel at 50.
    dense_probe = dense_stage
    if dense_limit < min(50, collection.count()):
        probe = collection.query(
            query_embeddings=[rag.embed_query(expanded_query)], n_results=min(50, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        dense_probe = _dense_docs_from_response(probe)

    bm25_stage = bm25.get_bm25_index().search(query=norm_query, top_n=60)
    bm25_docs = {item["doc_id"]: item for item in bm25_stage}
    dense_ranks = {item["doc_id"]: item["dense_rank"] for item in dense_stage}
    bm25_ranks = {item["doc_id"]: item["lexical_rank"] for item in bm25_stage}
    candidates: list[dict[str, Any]] = []
    for doc_id in set(dense_ranks) | set(bm25_ranks):
        dense_rank = dense_ranks.get(doc_id)
        lexical_rank = bm25_ranks.get(doc_id)
        dense_rrf = 1 / (60 + dense_rank) if dense_rank else 0.0
        lexical_rrf = 1.2 / (60 + lexical_rank) if lexical_rank else 0.0
        doc = dict(dense_docs[doc_id]) if doc_id in dense_docs else _as_doc(
            doc_id, bm25_docs[doc_id]["content"], bm25_docs[doc_id]["metadata"],
            distance=1.0, semantic_score=0.0, dense_rank=None,
        )
        meta = doc["metadata"]
        searchable = f"{meta.get('title', '')} {meta.get('tags', '')} {meta.get('solution', '')} {doc['content']}".lower()
        exact_boost = 0.005 * sum(token in searchable for token in exact_tokens)
        rrf_score = dense_rrf + lexical_rrf + exact_boost
        compatibility, reason = topic_compatibility(facets, meta)
        authority = rag.SOURCE_AUTHORITY_FACTORS.get(meta.get("source", "NO_SOURCE_KEY"), 1.0)
        doc.update({
            "lexical_rank": lexical_rank, "dense_rrf": dense_rrf, "lexical_rrf": lexical_rrf,
            "exact_contribution": exact_boost, "rrf_score": rrf_score,
            "topic_compatibility": compatibility, "topic_compatibility_reason": reason,
            "authority_factor": authority, "topic_adjusted_score": rrf_score * compatibility,
            "fusion_score": rrf_score * compatibility * authority,
        })
        doc["lexical_score"] = rag._lexical_score(expanded_query, meta, doc["content"])
        candidates.append(doc)
    candidates.sort(key=lambda item: (-item["fusion_score"], item["doc_id"]))
    max_fusion = candidates[0]["fusion_score"] if candidates else 1.0
    for item in candidates:
        base = max(item.get("semantic_score", 0.0), item.get("lexical_score", 0.0), 0.75 if item["fusion_score"] == max_fusion else 0.50)
        item["relevance_score"] = min(1.0, base * item["fusion_score"] / max_fusion) if max_fusion else 0.0
    candidates.sort(key=lambda item: (-item["relevance_score"], -item["fusion_score"], item["doc_id"]))
    primary, secondary, seen = [], [], set()
    for item in candidates:
        canonical = rag.get_canonical_source_id(item["doc_id"], item["metadata"])
        (primary if canonical not in seen else secondary).append(item)
        seen.add(canonical)
    return {
        "normalized_query": norm_query,
        "technical_topic": facets.predicted_topic,
        "dense": dense_probe,
        "dense_actual_pool": dense_stage,
        "bm25": bm25_stage,
        "union": candidates,
        "post_acl": candidates,
        "post_topic": candidates,
        "post_authority": candidates,
        "pre_dedup": candidates,
        "final": primary + secondary,
    }


def _collection_inventory(collection: Any) -> dict[str, Any]:
    data = collection.get(include=["metadatas", "documents"])
    docs = [_as_doc(doc_id, content, metadata) for doc_id, content, metadata in zip(
        data.get("ids", []), data.get("documents", []), data.get("metadatas", []), strict=True
    )]
    aliases: set[str] = set()
    by_canonical: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in docs:
        aliases |= doc_canonical_aliases(doc)
        by_canonical[rag.get_canonical_source_id(doc["doc_id"], doc["metadata"])].append(doc)
    return {"docs": docs, "aliases": aliases, "by_canonical": by_canonical}


def _target_details(expected: list[str], inventory: dict[str, Any]) -> dict[str, Any]:
    aliases = targets_canonical_aliases(expected)
    matches = [doc for doc in inventory["docs"] if doc_matches_targets(doc, aliases)]
    canonical = sorted({rag.get_canonical_source_id(doc["doc_id"], doc["metadata"]) for doc in matches})
    chunks = sum(len(inventory["by_canonical"][source]) for source in canonical)
    exact_missing = [target for target in expected if not (targets_canonical_aliases([target]) & inventory["aliases"])]
    return {
        "available": bool(matches), "expected_aliases": sorted(aliases), "canonical_sources": canonical,
        "chunk_count": chunks, "missing_expected_ids": exact_missing,
    }


def _top1_taxonomy(trace: dict[str, Any], aliases: set[str]) -> str:
    target = next((doc for doc in trace["union"] if doc_matches_targets(doc, aliases)), None)
    winner = trace["final"][0] if trace["final"] else None
    if target is None or winner is None:
        return "OTHER"
    if target.get("topic_compatibility", 1) < 1 and winner.get("topic_compatibility", 1) >= target.get("topic_compatibility", 1):
        return "TOPIC_PENALTY_TOO_STRONG"
    if target.get("rrf_score", 0) >= winner.get("rrf_score", 0) and target.get("authority_factor", 1) < winner.get("authority_factor", 1):
        return "AUTHORITY_OVERRANK"
    if target.get("dense_rank") is None and target.get("lexical_rank") is not None:
        return "DENSE_CONFUSION"
    if target.get("lexical_rank") is None and target.get("dense_rank") is not None:
        return "BM25_CONFUSION"
    if target.get("exact_contribution", 0) < winner.get("exact_contribution", 0):
        return "EXACT_TOKEN_UNDERWEIGHT"
    return "TOPIC_ROUTING_ERROR" if trace["technical_topic"] != "unknown" else "OTHER"


def _rate(value: int, total: int) -> float:
    return round(value * 100 / total, 2) if total else 0.0


def audit_collection(name: str, dataset: list[dict[str, Any]], audit_labels: bool) -> dict[str, Any]:
    inventory = _collection_inventory(_set_collection(name))
    stage_counts = Counter()
    recalls = {name: Counter() for name in ("dense", "bm25", "union")}
    domains: dict[str, Counter] = defaultdict(Counter)
    taxonomy: dict[str, list[str]] = defaultdict(list)
    cases: list[dict[str, Any]] = []
    start = time.perf_counter()
    for item in dataset:
        expected = item.get("expected_doc_ids") or []
        aliases = targets_canonical_aliases(expected)
        target = _target_details(expected, inventory)
        trace = _build_trace(item["query"])
        final = trace["final"][:5]
        # Guard the reconstructed trace against the actual runtime contract.
        runtime = rag.search_similar(item["query"], n_results=5)
        if [doc["doc_id"] for doc in runtime] != [doc["doc_id"] for doc in final]:
            raise RuntimeError(f"TRACE_RUNTIME_DIVERGENCE:{item.get('id')}")
        stage_hits = {stage: _stage_rank(trace[stage], aliases) for stage in trace if stage not in {"normalized_query", "technical_topic"}}
        for cutoff in (10, 20, 50):
            recalls["dense"][cutoff] += _stage_matches(trace["dense"][:cutoff], aliases)
            recalls["bm25"][cutoff] += _stage_matches(trace["bm25"][:cutoff], aliases)
            recalls["union"][cutoff] += (
                _stage_matches(trace["dense"][:cutoff], aliases)
                or _stage_matches(trace["bm25"][:cutoff], aliases)
            )
        final_rank = _stage_rank(final, aliases)
        domain = item.get("domain", "MISSING_DOMAIN")
        domains[domain]["cases"] += 1
        domains[domain]["available"] += target["available"]
        for cutoff in (1, 3, 5):
            domains[domain][f"hit_{cutoff}"] += bool(final_rank and final_rank <= cutoff)
        for cutoff in (20, 50):
            domains[domain][f"union_{cutoff}"] += _stage_matches(trace["union"][:cutoff], aliases)
        if not target["available"]:
            stage = "TARGET_UNAVAILABLE"
        elif not _stage_matches(trace["union"], aliases):
            stage = "TARGET_NOT_IN_ANY_CANDIDATE_POOL"
        elif not final_rank or final_rank > 5:
            stage = "TARGET_IN_POOL_RANK_GT5"
        elif final_rank > 3:
            stage = "TARGET_IN_TOP5_NOT_TOP3"
        elif final_rank > 1:
            stage = "TARGET_IN_TOP3_NOT_TOP1"
        else:
            stage = "TARGET_TOP1"
        stage_counts[stage] += 1
        pre_top5 = trace["pre_dedup"][:5]
        canonical_top5 = [rag.get_canonical_source_id(doc["doc_id"], doc["metadata"]) for doc in pre_top5]
        duplicate_chunks = len(canonical_top5) - len(set(canonical_top5))
        harm = bool(
            target["available"] and not _stage_matches(pre_top5, aliases)
            and _stage_matches(trace["pre_dedup"], aliases)
            and duplicate_chunks
        )
        category = _top1_taxonomy(trace, aliases) if target["available"] and final_rank != 1 else None
        if category:
            taxonomy[category].append(item["id"])
        cases.append({
            "case_id": item.get("id"), "domain": domain, "query": item["query"], "expected_doc_ids": expected,
            "target": target, "normalized_query": trace["normalized_query"], "technical_topic": trace["technical_topic"],
            "stage_ranks": stage_hits, "final_rank": final_rank, "failure_stage": stage,
            "top5_ids": [doc["doc_id"] for doc in final], "top1_taxonomy_heuristic": category,
            "pre_dedup_top5_ids": [doc["doc_id"] for doc in pre_top5],
            "pre_dedup_unique_canonical_sources": len(set(canonical_top5)),
            "pre_dedup_physical_chunks": len(pre_top5), "duplicate_chunk_harm": harm,
        })
    elapsed = time.perf_counter() - start
    total = len(dataset)
    return {
        "collection": name, "physical_documents": len(inventory["docs"]), "total": total,
        "target_available": sum(case["target"]["available"] for case in cases),
        "target_missing": sum(not case["target"]["available"] for case in cases),
        "recall": {channel: {f"@{cutoff}": _rate(values[cutoff], total) for cutoff in (10, 20, 50)} for channel, values in recalls.items()},
        "final": {f"@{cutoff}": _rate(sum(bool(case["final_rank"] and case["final_rank"] <= cutoff) for case in cases), total) for cutoff in (1, 3, 5)},
        "failure_stage_counts": dict(stage_counts),
        "domains": {domain: {
            "cases": values["cases"], "target_available": values["available"],
            **{f"hit@{cutoff}": _rate(values[f"hit_{cutoff}"], values["cases"]) for cutoff in (1, 3, 5)},
            **{f"union@{cutoff}": _rate(values[f"union_{cutoff}"], values["cases"]) for cutoff in (20, 50)},
        } for domain, values in sorted(domains.items())},
        "top1_taxonomy_heuristic": {kind: {"count": len(ids), "case_ids": ids} for kind, ids in sorted(taxonomy.items())},
        "chunk_duplication": {
            "avg_unique_sources_pre_dedup_top5": round(sum(case["pre_dedup_unique_canonical_sources"] for case in cases) / total, 3),
            "avg_physical_chunks_pre_dedup_top5": round(sum(case["pre_dedup_physical_chunks"] for case in cases) / total, 3),
            "cases_with_duplicate_source_chunks_top5": sum(case["pre_dedup_unique_canonical_sources"] < case["pre_dedup_physical_chunks"] for case in cases),
            "cases_harmed_by_duplicate_chunks": sum(case["duplicate_chunk_harm"] for case in cases),
            "avg_unique_sources_final_top5": round(sum(len({
                rag.get_canonical_source_id(doc_id, {}) for doc_id in case["top5_ids"]
            }) for case in cases) / total, 3),
            "avg_physical_chunks_final_top5": round(sum(len(case["top5_ids"]) for case in cases) / total, 3),
        },
        "latency_per_query_ms": round(elapsed * 1000 / total, 2), "cases": cases,
    }


def dataset_integrity(dataset: list[dict[str, Any]], v3: dict[str, Any], v4: dict[str, Any]) -> dict[str, Any]:
    ids = [item.get("id") for item in dataset]
    malformed = [
        item.get("id", "<missing>") for item in dataset
        if not isinstance(item.get("id"), str) or not CASE_ID_PATTERN.fullmatch(item["id"])
        or not isinstance(item.get("query"), str) or not item["query"].strip()
        or not isinstance(item.get("expected_doc_ids"), list) or not item["expected_doc_ids"]
        or any(not isinstance(target, str) or not target.strip() for target in item["expected_doc_ids"])
    ]
    duplicates = sorted(case_id for case_id, count in Counter(ids).items() if count > 1)
    return {
        "total_cases": len(dataset), "valid_cases": len(dataset) - len(malformed), "malformed_cases": malformed,
        "duplicate_case_ids": duplicates,
        "v3": {"available": v3["target_available"], "missing": v3["target_missing"]},
        "v4": {"available": v4["target_available"], "missing": v4["target_missing"]},
        "negative_fields_present": any("hard_negative_source_ids" in item for item in dataset),
    }


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    v3 = audit_collection(V3, dataset, audit_labels=False)
    v4 = audit_collection(V4, dataset, audit_labels=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(), "benchmark": str(DATASET_PATH),
        "integrity": dataset_integrity(dataset, v3, v4), "v3": v3, "v4": v4,
        "match_contract": "A hit is any retrieved document whose doc_id, metadata.source_id, metadata.canonical_source_id, or metadata.parent_document_id shares a normalized canonical alias with any expected_doc_ids entry. For web-/p0- chunk IDs, the chunk suffix and web- prefix aliases are also recognized.",
        "trace_contract": "A3 consumes 40 dense physical chunks for final top-5 retrieval and 60 BM25 chunks. Dense@50 is a non-mutating raw-channel probe; union@N means a target is present in either dense@N or BM25@N. Failure-stage classification uses the actual A3 union (dense@40 plus BM25@60). Final applies A3 canonical-source diversity before top-K.",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"integrity": report["integrity"], "v3": {key: v3[key] for key in ("recall", "final", "failure_stage_counts", "chunk_duplication")}, "v4": {key: v4[key] for key in ("recall", "final", "failure_stage_counts", "chunk_duplication")}}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
