"""Test edge cases: irrelevant internal KB vs highly relevant external web docs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.scripts.experiment_authority import search_custom

# Test: Synthetic query where ONLY external web doc is relevant
# e.g. Microsoft Windows error code specific to vendor
print("Checking that irrelevant internal KB does NOT beat relevant web docs...")
results = search_custom("Khắc phục lỗi kích hoạt bản quyền Windows 0x803FA067", n_results=5, authority_weight=1.40)
for idx, r in enumerate(results, 1):
    m = r.get("metadata", {}) or {}
    print(f"Rank {idx}: {r['doc_id']} | Rel={r['relevance_score']:.4f} | Source={m.get('source')} | Title={m.get('title')}")
