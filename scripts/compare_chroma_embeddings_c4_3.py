"""Read-only old/new retrieval comparison for the C4.3 Chroma migration."""
# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.rag_service import (  # noqa: E402
    embed_query_for_collection,
    get_chroma_client,
    search_similar,
)


QUERIES = [
    ("vpn", "Hướng dẫn kết nối VPN", ("vpn",)),
    ("outlook", "Outlook không gửi được email", ("outlook", "email")),
    ("password", "Quên mật khẩu tài khoản", ("mật khẩu", "password", "windows")),
    ("service_request", "Quy trình Service Request là gì?", ("yêu cầu", "service", "request")),
    ("hardware", "Yêu cầu cấp laptop", ("laptop", "máy tính", "hardware")),
    ("access_vpn", "Xin quyền truy cập VPN", ("vpn", "truy cập", "access")),
    ("software_license", "Đăng ký phần mềm Microsoft 365", ("office", "microsoft", "phần mềm", "license")),
    ("unsupported", "Cách chăm sóc cây cảnh trong nhà", ()),
]


def _rows(collection, query: str, limit: int = 5) -> list[dict]:
    result = collection.query(
        query_embeddings=[embed_query_for_collection(query, collection)],
        n_results=limit,
        include=["metadatas", "distances"],
    )
    return [
        {
            "doc_id": doc_id,
            "title": str((metadata or {}).get("title") or ""),
            "category": str((metadata or {}).get("category") or ""),
            "distance": round(float(distance), 6),
        }
        for doc_id, metadata, distance in zip(
            result.get("ids", [[]])[0],
            result.get("metadatas", [[]])[0],
            result.get("distances", [[]])[0],
        )
    ]


def _hit(rows: list[dict], expected_tokens: tuple[str, ...]) -> bool | None:
    if not expected_tokens:
        return None
    return any(
        any(token in f"{row['title']} {row['category']}".casefold() for token in expected_tokens)
        for row in rows
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="helpdesk_kb_multilingual_v1")
    parser.add_argument("--target", default="helpdesk_kb_multilingual_v2_sentence_transformer")
    parser.add_argument(
        "--report", default="eval/results/chroma_embedding_retrieval_comparison_c4_3.json"
    )
    args = parser.parse_args()

    client = get_chroma_client()
    source = client.get_collection(args.source)
    target = client.get_collection(args.target)
    query_rows = []
    for query_id, query, expected_tokens in QUERIES:
        old_rows = _rows(source, query)
        new_rows = _rows(target, query)
        query_rows.append(
            {
                "id": query_id,
                "query": query,
                "expected_title_or_category_tokens": list(expected_tokens),
                "old_top_5": old_rows,
                "new_top_5": new_rows,
                "old_expected_class_in_top_5": _hit(old_rows, expected_tokens),
                "new_expected_class_in_top_5": _hit(new_rows, expected_tokens),
            }
        )

    # This uses the normal, ACL-aware retrieval path selected by runtime.
    acl = {}
    for company_unit in ("real_estate", "corporate"):
        acl[company_unit] = [
            {"doc_id": row["doc_id"], "title": row["metadata"].get("title")}
            for row in search_similar(
                "SAP không đăng nhập được", n_results=5, user_company_unit=company_unit
            )
        ]

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_collection": args.source,
        "target_collection": args.target,
        "source_count": source.count(),
        "target_count": target.count(),
        "queries": query_rows,
        "acl_query": "SAP không đăng nhập được",
        "acl_results": acl,
        "security_expectation": {
            "unauthorized_company_unit_must_not_return": ["kb-019", "kb-020"],
            "corporate_should_return_restricted_sap_source": True,
        },
    }
    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
