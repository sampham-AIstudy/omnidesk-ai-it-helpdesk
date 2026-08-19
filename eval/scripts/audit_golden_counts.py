"""Audit retrieval_golden_v1.json cases and scorable status."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

golden_path = ROOT_DIR / "eval" / "retrieval_golden_v1.json"
data = json.load(open(golden_path, encoding="utf-8"))
cases = data["cases"]

print(f"Total cases in golden dataset: {len(cases)}")

categories = {}
scorable_by_cat = {}
non_scorable_by_cat = {}

for c in cases:
    cat = c["category_group"]
    categories.setdefault(cat, []).append(c["id"])
    expected = c.get("expected_source_ids", [])
    if expected:
        scorable_by_cat.setdefault(cat, []).append(c["id"])
    else:
        non_scorable_by_cat.setdefault(cat, []).append(c["id"])

print("\nCategory breakdown:")
total_scorable = 0
total_non_scorable = 0
for cat, ids in sorted(categories.items()):
    sc = len(scorable_by_cat.get(cat, []))
    nsc = len(non_scorable_by_cat.get(cat, []))
    total_scorable += sc
    total_non_scorable += nsc
    print(f"  {cat:<25}: total={len(ids)}, scorable={sc}, non_scorable={nsc}")
    if nsc > 0:
        print(f"    Non-scorable IDs: {non_scorable_by_cat[cat]}")

print(f"\nOverall: Total={len(cases)}, Scorable={total_scorable}, Non-scorable={total_non_scorable}")
