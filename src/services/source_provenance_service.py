"""Canonical, user-navigable provenance payloads for RAG evidence."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote


_TICKET_NUMBER_RE = re.compile(r"\b(?:INC|REQ)-[A-Za-z0-9-]+\b", re.IGNORECASE)


def source_id_for_document(document: dict[str, Any]) -> str:
    """Return only the persisted ID that was supplied by retrieval."""
    metadata = document.get("metadata", {}) or {}
    value = document.get("doc_id") or metadata.get("source_id") or metadata.get("chroma_id")
    return str(value) if value else ""


def knowledge_source_payload(document: dict[str, Any]) -> dict[str, str]:
    """Build a link target without inventing a URL or external source.

    An internal RAG document always opens through the access-controlled source
    reader.  A verified ``source_url`` is the sole exception: it is an actual
    external source and may be opened directly by the browser.
    """
    metadata = document.get("metadata", {}) or {}
    label = str(metadata.get("title") or "Knowledge Base")
    source_url = str(metadata.get("source_url") or "").strip()
    if source_url.startswith(("https://", "http://")):
        return {"label": label, "kind": "web", "url": source_url}

    # A lesson explicitly derived from a ticket should lead to the original,
    # ACL-checked ticket transcript rather than duplicate its generated summary
    # in a detached source-reader view.
    ticket_id = metadata.get("source_ticket_id") or metadata.get("ticket_id")
    ticket_number = str(metadata.get("source_ticket_number") or "").strip()
    has_ticket_provenance = bool(ticket_id or ticket_number)
    if not ticket_number:
        title_match = _TICKET_NUMBER_RE.search(label)
        ticket_number = title_match.group(0) if title_match else ""
    if ticket_id:
        return {"label": f"Ticket #{ticket_number or ticket_id}", "kind": "ticket", "ticket_id": str(ticket_id)}
    if ticket_number and (has_ticket_provenance or label.casefold().startswith("kb bài học từ ticket")):
        return {
            "label": f"Ticket #{ticket_number}",
            "kind": "ticket",
            "url": f"/employee/tickets/reference/{quote(ticket_number, safe='')}",
        }

    source_id = source_id_for_document(document)
    payload = {"label": label, "kind": "kb"}
    if source_id:
        payload["source_id"] = source_id
        payload["url"] = f"/employee/kb?source_id={quote(source_id, safe='')}"
    return payload
