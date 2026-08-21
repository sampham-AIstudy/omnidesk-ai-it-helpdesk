"""Read-only, tenant-isolated aggregate report for retrieval outcome telemetry.

The report never selects raw chat, ticket, or web-research text.  It reads only
the closed-topic outcome table introduced for Step 8B.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings  # noqa: E402

# Deliberately small and documented; owners can tune this policy separately
# from retrieval ranking or source authority.
BUSINESS_CRITICALITY: dict[str, float] = {
    "vpn.forticlient": 1.5,
    "vpn.internal_resource_access": 1.5,
    "network.tcp_connectivity": 1.4,
    "network.port_timeout": 1.4,
    "network.connection_refused": 1.4,
    "network.service_not_listening": 1.4,
    "network.firewall_acl": 1.4,
    "http.status_403": 1.2,
    "dns": 1.3,
    "dhcp": 1.3,
    "routing": 1.3,
    "proxy": 1.2,
    "network.smb_network_drive": 1.2,
}
DEFAULT_CRITICALITY = 1.0


def _sqlite_path(database_url: str) -> Path:
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("report_knowledge_gaps.py supports the configured SQLite datastore only")
    return Path(database_url.removeprefix(prefix)).resolve()


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def build_report_rows(
    connection: sqlite3.Connection,
    *,
    tenant_scope: str | None = None,
    criticality: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate outcome-only data; always keep tenant scopes separate."""
    query = """
        SELECT tenant_scope, normalized_topic,
               COUNT(*) AS query_count,
               SUM(CASE WHEN retrieval_required THEN 1 ELSE 0 END) AS retrieval_required_count,
               SUM(CASE WHEN no_evidence THEN 1 ELSE 0 END) AS no_evidence_count,
               SUM(CASE WHEN insufficient_evidence THEN 1 ELSE 0 END) AS insufficient_evidence_count,
               AVG(top_score) AS avg_top_score,
               SUM(CASE WHEN web_research_triggered THEN 1 ELSE 0 END) AS web_research_count,
               SUM(CASE WHEN web_research_failure_category IS NOT NULL THEN 1 ELSE 0 END) AS web_research_failure_count,
               SUM(CASE WHEN hitl_or_escalation THEN 1 ELSE 0 END) AS hitl_count,
               SUM(CASE WHEN is_knowledge_gap THEN 1 ELSE 0 END) AS knowledge_gap_count
        FROM knowledge_gap_events
    """
    params: tuple[str, ...] = ()
    if tenant_scope:
        query += " WHERE tenant_scope = ?"
        params = (tenant_scope,)
    query += " GROUP BY tenant_scope, normalized_topic"
    rows = connection.execute(query, params).fetchall()
    output: list[dict[str, Any]] = []
    for row in rows:
        values = dict(row) if isinstance(row, sqlite3.Row) else dict(zip(
            ["tenant_scope", "normalized_topic", "query_count", "retrieval_required_count", "no_evidence_count", "insufficient_evidence_count", "avg_top_score", "web_research_count", "web_research_failure_count", "hitl_count", "knowledge_gap_count"], row
        ))
        query_count = int(values["query_count"] or 0)
        gap_count = int(values.pop("knowledge_gap_count") or 0)
        criticality_value = (criticality or BUSINESS_CRITICALITY).get(
            values["normalized_topic"], DEFAULT_CRITICALITY
        )
        values["avg_top_score"] = round(float(values["avg_top_score"]), 4) if values["avg_top_score"] is not None else None
        values["no_evidence_rate"] = _rate(int(values["no_evidence_count"] or 0), query_count)
        values["web_research_rate"] = _rate(int(values["web_research_count"] or 0), query_count)
        values["HITL_rate"] = _rate(int(values["hitl_count"] or 0), query_count)
        values["knowledge_gap_rate"] = _rate(gap_count, query_count)
        values["business_criticality"] = criticality_value
        values["priority_score"] = round(query_count * values["knowledge_gap_rate"] * criticality_value, 4)
        output.append(values)
    return sorted(output, key=lambda item: (-item["priority_score"], item["tenant_scope"], item["normalized_topic"]))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only knowledge-gap telemetry report")
    parser.add_argument("--database", type=Path, help="SQLite database path; defaults to configured runtime DB")
    parser.add_argument("--tenant", help="Optional exact tenant scope; aggregation remains tenant-isolated")
    parser.add_argument("--criticality-file", type=Path, help="Optional JSON object mapping closed topics to positive weights")
    parser.add_argument("--format", choices=("json", "table"), default="json")
    args = parser.parse_args(list(argv) if argv is not None else None)
    path = (args.database or _sqlite_path(get_settings().database_url)).resolve()
    criticality: dict[str, float] | None = None
    if args.criticality_file:
        payload = json.loads(args.criticality_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or any(not isinstance(key, str) or not isinstance(value, (int, float)) or value <= 0 for key, value in payload.items()):
            parser.error("--criticality-file must be a JSON object of closed topic names to positive numeric weights")
        criticality = {key: float(value) for key, value in payload.items()}
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = build_report_rows(connection, tenant_scope=args.tenant, criticality=criticality)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            rows = []
        else:
            raise
    finally:
        connection.close()
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(" | ".join(f"{key}={value}" for key, value in row.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
