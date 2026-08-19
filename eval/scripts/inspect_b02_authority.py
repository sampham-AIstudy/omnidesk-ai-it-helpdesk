"""Inspect RET-B02 scores across authority configs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.scripts.experiment_authority import search_custom

golden = json.load(open(ROOT_DIR / "eval" / "retrieval_golden_v1.json", encoding="utf-8"))["cases"]
case_b02 = [c for c in golden if c["id"] == "RET-B02"][0]
print("Query:", case_b02["query"])
print("Expected:", case_b02.get("expected_doc_ids", []))

for name, auth_w, dedup in [
    ("A. Locked Hybrid", 1.10, False),
    ("B. Auth 1.25", 1.25, False),
    ("C. Auth 1.35", 1.35, False),
    ("D. Auth 1.50", 1.50, False),
    ("E. Dedup only (Auth 1.10)", 1.10, True),
    ("F. Dedup + Auth 1.25", 1.25, True),
    ("G. Dedup + Auth 1.35", 1.35, True),
]:
    results = search_custom(
        case_b02["query"],
        n_results=5,
        authority_weight=auth_w,
        collapse_duplicates=dedup,
    )
    print(f"\n--- {name} ---")
    for idx, r in enumerate(results, 1):
        m = r.get("metadata", {}) or {}
        print(f"Rank {idx}: {r['doc_id']} | Rel={r['relevance_score']:.4f} | Fusion={r['fusion_score']:.4f} | Dense_r={r['dense_rank']} | BM25_r={r['lexical_rank']} | Source={m.get('source')} | Title={m.get('title')}")
