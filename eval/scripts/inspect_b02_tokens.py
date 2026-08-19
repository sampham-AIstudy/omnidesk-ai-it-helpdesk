"""Inspect tokens and fusion components for RET-B02."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.services.query_normalization_service import (
    extract_exact_technical_tokens,
    normalize_informal_query,
)
from src.services.rag_service import get_collection

q = "BitLocker yêu cầu recovery key khi khởi động laptop"
norm_q = normalize_informal_query(q)
tokens = extract_exact_technical_tokens(q) | extract_exact_technical_tokens(norm_q)
print("Query:", q)
print("Norm query:", norm_q)
print("Extracted exact technical tokens:", tokens)

col = get_collection()
data = col.get(ids=["kb-015", "web-bitlocker-recovery-001", "web-bitlocker-recovery-002"], include=["metadatas", "documents"])
for did, meta, doc in zip(data["ids"], data["metadatas"], data["documents"]):
    print(f"\n--- {did} ---")
    print("Title:", meta.get("title"))
    print("Tags:", meta.get("tags"))
    print("Source:", meta.get("source"))
    searchable_text = f"{meta.get('title', '')} {meta.get('tags', '')} {meta.get('solution', '')} {doc}".lower()
    matches = [t for t in tokens if t in searchable_text]
    print("Exact token matches in doc:", matches)
