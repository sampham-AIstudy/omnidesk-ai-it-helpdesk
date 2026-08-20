"""
Audit Logging Module
Gathers security events, decisions, tool calls, and exports formatted JSON audit logs.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_audit_records: list[dict[str, Any]] = []


def record_audit_event(
    action: str,
    decision: str,
    reason: str,
    ticket_id: str = "",
    tenant_id: str = "",
    user_id: str = "",
    policy_id: str = "",
    category: str = "",
    confidence: float = 1.0,
    risk: str = "LOW",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a structured security audit event."""
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "ticket_id": ticket_id or "N/A",
        "tenant_id": tenant_id or "default",
        "user_id": user_id or "anonymous",
        "action": action,
        "decision": decision,
        "reason": reason,
        "policy_id": policy_id or "GENERAL_POLICY",
        "category": category,
        "confidence": confidence,
        "risk": risk,
        "agent": "guardrail-agent",
        "metadata": metadata or {},
    }
    _audit_records.append(event)
    logger.info(f"[AUDIT] {action} -> {decision}: {reason}")
    return event


def export_json(output_path: str = "outputs/audit_log.json") -> None:
    """Export stored audit log events to JSON file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(_audit_records, f, indent=2, ensure_ascii=False)
    logger.info(f"Exported {len(_audit_records)} audit log entries to {output_path}")


def get_audit_records() -> list[dict[str, Any]]:
    return _audit_records
