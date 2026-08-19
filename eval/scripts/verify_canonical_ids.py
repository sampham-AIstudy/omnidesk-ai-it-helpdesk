"""Verify canonical source ID derivation across entire Chroma collection."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import re
import urllib.parse
from typing import Any
from src.services.rag_service import get_collection


def get_canonical_source_id(doc_id: str, metadata: dict[str, Any] | None = None) -> str:
    """Derive canonical logical document ID for deduplication and grouping."""
    meta = metadata or {}
    source_url = meta.get("source_url", "").strip()
    if source_url:
        try:
            parsed = urllib.parse.urlparse(source_url)
            norm_url = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
            if parsed.query:
                norm_url = f"{norm_url}?{parsed.query}"
            return f"url:{norm_url}"
        except Exception:
            return f"url:{source_url.lower().rstrip('/')}"

    if meta.get("parent_id"):
        return f"parent:{meta['parent_id']}"
    if meta.get("canonical_source_id"):
        return f"canon:{meta['canonical_source_id']}"

    if doc_id.startswith("web-"):
        m = re.match(r"^(web-.+)-\d{3,}$", doc_id)
        if m:
            return f"web_base:{m.group(1)}"

    if doc_id.startswith("kb-"):
        m = re.match(r"^(kb-\d+)[_-](?:chunk|part|c)\d+$", doc_id, re.IGNORECASE)
        if m:
            return f"kb_base:{m.group(1)}"
        return f"kb:{doc_id}"

    return doc_id


col = get_collection()
data = col.get(include=["metadatas"])
ids = data["ids"]
metas = data["metadatas"]

canonical_map = {}
for did, meta in zip(ids, metas):
    cid = get_canonical_source_id(did, meta)
    canonical_map.setdefault(cid, []).append(did)

print(f"Total physical documents: {len(ids)}")
print(f"Total unique canonical sources: {len(canonical_map)}")

multi_chunk_sources = {k: v for k, v in canonical_map.items() if len(v) > 1}
print(f"Multi-chunk canonical sources: {len(multi_chunk_sources)}")
for cid, chunk_ids in list(multi_chunk_sources.items())[:10]:
    print(f"  {cid} -> {chunk_ids}")

# Verify kb-015 and kb-016 are distinct
assert get_canonical_source_id("kb-015") != get_canonical_source_id("kb-016")
assert get_canonical_source_id("kb-015") == "kb:kb-015"
assert get_canonical_source_id("kb-016") == "kb:kb-016"
# Verify web bitlocker chunks match
assert get_canonical_source_id("web-bitlocker-recovery-001", metas[ids.index("web-bitlocker-recovery-001")]) == get_canonical_source_id("web-bitlocker-recovery-002", metas[ids.index("web-bitlocker-recovery-002")])
print("\nAll canonical assertions passed!")
