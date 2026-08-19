"""Audit RET-B06 candidates and check local available cross-encoder models."""
from __future__ import annotations

import json
import os
from pathlib import Path

import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.services.rag_service import search_similar

golden = json.load(open(ROOT_DIR / "eval" / "retrieval_golden_v1.json", encoding="utf-8"))["cases"]
case_b06 = [c for c in golden if c["id"] == "RET-B06"][0]
print("=== CASE RET-B06 ===")
print("Query:", case_b06["query"])
print("Expected:", case_b06["expected_source_ids"])
print("Acceptable:", case_b06["acceptable_source_ids"])
print("Forbidden:", case_b06["forbidden_source_ids"])

# Top 15 hybrid results
docs = search_similar(case_b06["query"], n_results=15)
for idx, d in enumerate(docs, 1):
    meta = d.get("metadata", {}) or {}
    title = meta.get("title", "N/A")
    source = meta.get("source", "N/A")
    print(
        f"Rank {idx}: doc_id={d.get('doc_id')} "
        f"(rel={d.get('relevance_score', 0):.4f}, "
        f"fusion={d.get('fusion_score', 0):.4f}, "
        f"dense_r={d.get('dense_rank')}, "
        f"bm25_r={d.get('lexical_rank')}) "
        f"- [{source}] {title}"
    )

# Check cache directory
hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface/hub"))
print("\nHuggingFace cache path:", hf_home)
if os.path.exists(hf_home):
    models = [m for m in os.listdir(hf_home) if os.path.isdir(os.path.join(hf_home, m))]
    print("Cached models in HF cache:", models)
