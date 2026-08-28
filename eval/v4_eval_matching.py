"""Canonical alias extraction and matching for V4 evaluation benchmarks."""
from __future__ import annotations

import re
from typing import Any


def canonical_aliases(ident: str | None) -> set[str]:
    """Generate normalized, non-empty alias keys for exact set matching."""
    if not ident:
        return set()
    s = str(ident).strip().lower()
    if not s:
        return set()
    aliases = {s}
    # For multi-chunk web or p0 documents (e.g. web-name-001, p0-name-c001),
    # extract the base document key
    if s.startswith("web-") or s.startswith("p0-"):
        base = re.sub(r"(-c?\d{3,4})$", "", s)
        if base:
            aliases.add(base)
        if base.startswith("web-") and len(base) > 4:
            aliases.add(base[4:])
        if s.startswith("web-") and len(s) > 4:
            aliases.add(s[4:])
    return {a for a in aliases if a}


def doc_canonical_aliases(doc: dict[str, Any] | None) -> set[str]:
    """Collect all non-empty canonical alias keys for a retrieved document."""
    if not doc:
        return set()
    aliases: set[str] = set()
    if doc_id := doc.get("doc_id") or doc.get("id"):
        aliases |= canonical_aliases(doc_id)
    meta = doc.get("metadata") or {}
    if source_id := meta.get("source_id"):
        aliases |= canonical_aliases(source_id)
    if canon_id := meta.get("canonical_source_id"):
        aliases |= canonical_aliases(canon_id)
    if parent_id := meta.get("parent_document_id"):
        aliases |= canonical_aliases(parent_id)
    return {a for a in aliases if a}


def targets_canonical_aliases(targets: list[str] | set[str]) -> set[str]:
    """Collect all non-empty canonical alias keys for expected/negative targets."""
    aliases: set[str] = set()
    for t in targets:
        aliases |= canonical_aliases(t)
    return {a for a in aliases if a}


def doc_matches_targets(doc: dict[str, Any] | None, target_aliases: set[str]) -> bool:
    """Check if a document matches any target via exact alias set intersection."""
    if not doc or not target_aliases:
        return False
    return bool(doc_canonical_aliases(doc) & target_aliases)
