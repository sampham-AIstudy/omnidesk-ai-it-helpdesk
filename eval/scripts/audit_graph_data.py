import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.environ.setdefault("HF_DEACTIVATE_ASYNC_LOAD", "1")

from src.services.rag_service import get_collection

def audit():
    col = get_collection()
    count = col.count()
    data = col.get(include=["metadatas", "documents"])
    ids = data["ids"]
    metadatas = data["metadatas"]
    docs = data["documents"]

    print(f"Total documents: {count}")
    
    key_counts = Counter()
    source_counts = Counter()
    category_counts = Counter()
    topic_counts = Counter()
    company_unit_counts = Counter()
    department_counts = Counter()
    has_parent_id = 0
    has_chunk_index = 0
    has_canonical_source_id = 0
    has_title = 0
    has_tags = 0

    for m in metadatas:
        if not m:
            continue
        for k in m.keys():
            key_counts[k] += 1
        source_counts[str(m.get("source") or m.get("source_type"))] += 1
        category_counts[str(m.get("category"))] += 1
        topic_counts[str(m.get("topic"))] += 1
        company_unit_counts[str(m.get("company_unit"))] += 1
        department_counts[str(m.get("department"))] += 1
        if m.get("parent_id") or m.get("parent_document_id"):
            has_parent_id += 1
        if m.get("chunk_index") is not None:
            has_chunk_index += 1
        if m.get("canonical_source_id"):
            has_canonical_source_id += 1
        if m.get("title"):
            has_title += 1
        if m.get("tags"):
            has_tags += 1

    print("\nMetadata Key Frequencies:")
    for k, v in key_counts.most_common():
        print(f"  {k}: {v}/{count}")

    print("\nSource Breakdown:")
    for s, v in source_counts.most_common():
        print(f"  {s}: {v}")

    print(f"\nParent ID count: {has_parent_id}")
    print(f"Chunk index count: {has_chunk_index}")
    print(f"Canonical source ID count: {has_canonical_source_id}")
    print(f"Title count: {has_title}")
    print(f"Tags count: {has_tags}")

if __name__ == "__main__":
    audit()
