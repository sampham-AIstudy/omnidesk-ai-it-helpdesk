"""Audit source metadata in Chroma collection for STEP 4."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.retrieval_metrics import evaluate_single_case
from src.services.rag_service import get_collection, search_similar


def audit_metadata():
    col = get_collection()
    data = col.get(include=["metadatas", "documents"])
    ids = data.get("ids", [])
    metas = data.get("metadatas", [])
    docs = data.get("documents", [])

    print(f"Total documents in collection: {len(ids)}")

    # 1. Group IDs by prefix/source type
    prefixes = {}
    source_types = {}
    for doc_id, meta in zip(ids, metas):
        prefix = doc_id.split("-")[0] if "-" in doc_id else "other"
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
        st = (meta or {}).get("source", "NO_SOURCE_KEY")
        source_types[st] = source_types.get(st, 0) + 1

    print("\nID Prefix breakdown:", prefixes)
    print("Source Type metadata breakdown:", source_types)

    # 2. Inspect specific documents related to BitLocker
    target_ids = ["kb-015", "web-bitlocker-recovery-001", "web-bitlocker-recovery-002"]
    print("\n=== Target Document Inspection ===")
    for tid in target_ids:
        if tid in ids:
            idx = ids.index(tid)
            print(f"\n--- ID: {tid} ---")
            print(f"Metadata keys: {list(metas[idx].keys())}")
            print(f"Metadata: {json.dumps(metas[idx], ensure_ascii=False, indent=2)}")
            print(f"Content (first 250 chars): {docs[idx][:250]}...")
        else:
            print(f"\nID: {tid} NOT FOUND in collection!")

    # 3. Check RET-B02 in search_similar()
    golden = json.load(open(ROOT_DIR / "eval" / "retrieval_golden_v1.json", encoding="utf-8"))["cases"]
    case_b02 = [c for c in golden if c["id"] == "RET-B02"][0]
    print("\n=== RET-B02 Hybrid Retrieval Debug ===")
    print("Query:", case_b02["query"])
    results = search_similar(case_b02["query"], n_results=10)
    for rank, r in enumerate(results, 1):
        m = r.get("metadata", {}) or {}
        print(
            f"Rank {rank}: {r.get('doc_id')} | "
            f"Rel={r.get('relevance_score', 0):.4f} | "
            f"Fusion={r.get('fusion_score', 0):.4f} | "
            f"Dense_r={r.get('dense_rank')} | "
            f"BM25_r={r.get('lexical_rank')} | "
            f"Source={m.get('source')} | "
            f"Title={m.get('title')}"
        )


if __name__ == "__main__":
    audit_metadata()
