"""Stable-ID fixture snapshot builder for enterprise evaluation v1.2."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import sha256_text_file
from eval.fixture_integrity import EvidenceMode, audit_fixture_integrity
from src.data.knowledge_base import get_all_kb_entries

ROOT = Path(__file__).parent.parent
SNAPSHOT_VERSION = "enterprise-context-snapshot-v1.2"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_text_file(path)


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _normalized_title(value: str) -> str:
    value = "".join(char for char in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(char) != "Mn")
    return " ".join(value.replace("đ", "d").split())


def resolve_source(
    source_id: str, kb: dict[str, dict[str, Any]], fixtures: dict[str, dict[str, Any]], *, acceptable_titles: list[str] | None = None,
) -> tuple[str, dict[str, Any], str] | None:
    """Stable ID first; title matching is an explicit final fallback only."""
    if source_id in kb:
        return source_id, kb[source_id], "INTERNAL"
    if source_id in fixtures:
        return source_id, fixtures[source_id], "EVAL_FIXTURE"
    targets = {_normalized_title(title) for title in acceptable_titles or []}
    for candidate_id, source in kb.items():
        if _normalized_title(source["title"]) in targets:
            return candidate_id, source, "INTERNAL"
    return None


def _source_payload(source_id: str, title: str, content: str, source_type: str, *, provenance: str) -> dict[str, Any]:
    return {
        "doc_id": source_id,
        "content": content,
        "metadata": {
            "source_id": source_id, "source_type": source_type, "title": title,
            "snapshot_version": SNAPSHOT_VERSION, "content_hash": _content_hash(content), "provenance": provenance,
        },
    }


def build_snapshot(golden: list[dict[str, Any]], mapping: dict[str, Any]) -> dict[str, Any]:
    kb = {entry["id"]: entry for entry in get_all_kb_entries()}
    fixtures = mapping["evaluation_fixtures"]
    contexts: dict[str, list[dict[str, Any]]] = {}
    mode_overrides: dict[str, EvidenceMode] = {}
    requirements: dict[str, dict[str, Any]] = {}
    for case in golden:
        case_id = case["id"]
        item = mapping["entries"].get(case_id)
        contexts[case_id] = []
        if not item:
            continue
        mode = EvidenceMode(item["expected_evidence_mode"])
        mode_overrides[case_id] = mode
        requirements[case_id] = item
        for source_id in item["acceptable_source_ids"]:
            resolved = resolve_source(source_id, kb, fixtures, acceptable_titles=item.get("acceptable_titles"))
            if resolved is None:
                raise ValueError(f"EVAL_FIXTURE_ERROR: unresolved stable source ID {source_id} for {case_id}")
            resolved_id, source, source_type = resolved
            if source_type == "INTERNAL":
                content = f"{source.get('content', '')}\n{source.get('solution', '')}".strip()
                contexts[case_id].append(_source_payload(resolved_id, source["title"], content, "INTERNAL", provenance="frozen KB fixture"))
            else:
                contexts[case_id].append(_source_payload(resolved_id, source["title"], source["content"], "EVAL_FIXTURE", provenance=source["provenance"]))
    audit = audit_fixture_integrity(golden, contexts, mode_overrides=mode_overrides, requirements=requirements)
    if audit["eval_fixture_error_count"]:
        errors = ", ".join(row["id"] for row in audit["cases"] if row["integrity"] != "PASS")
        raise ValueError(f"EVAL_FIXTURE_ERROR: fixture integrity failed for {errors}")
    return {
        "__metadata__": {
            "snapshot_version": SNAPSHOT_VERSION,
            "golden_sha256": sha256_file(ROOT / "eval" / "golden_testset_enterprise.json"),
            "manifest_sha256": sha256_file(ROOT / "eval" / "evaluation_manifest.json"),
            "source_mapping_sha256": sha256_file(ROOT / "eval" / "source_mappings_enterprise_v1_2.json"),
            "kb_fixture_sha256": sha256_file(ROOT / "src" / "data" / "knowledge_base.py"),
            "ticket_fixture_sha256": sha256_file(ROOT / "tests" / "conftest.py"),
            "builder_version": "stable-id-builder-v1.2",
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "fixture_integrity": audit,
        },
        **contexts,
    }


def main() -> None:
    golden = json.loads((ROOT / "eval" / "golden_testset_enterprise.json").read_text(encoding="utf-8"))
    mapping = json.loads((ROOT / "eval" / "source_mappings_enterprise_v1_2.json").read_text(encoding="utf-8"))
    snapshot = build_snapshot(golden, mapping)
    target = ROOT / "eval" / "snapshots" / "enterprise_context_snapshot_v1_2.json"
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(target), "fixture_integrity": snapshot["__metadata__"]["fixture_integrity"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
