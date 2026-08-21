"""Experiment script comparing baseline and hybrid configurations."""
from __future__ import annotations

import gc
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

# Ensure root dir in path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation
from src.services.rag_service import (
    _expand_query,
    _metadata_allowed,
    _normalize_search_text,
    embed_query,
    get_collection,
    scan_indirect_injection,
    search_similar,
)

INFORMAL_MAP = {
    "ko": "không",
    "k": "không",
    "khong": "không",
    "dc": "được",
    "đc": "được",
    "duoc": "được",
    "cty": "công ty",
    "cong ty": "công ty",
    "mk": "mật khẩu",
    "mat khau": "mật khẩu",
    "sdt": "số điện thoại",
    "sđt": "số điện thoại",
    "auth": "authentication",
    "login": "đăng nhập",
    "dang nhap": "đăng nhập",
    "sync": "đồng bộ",
    "dong bo": "đồng bộ",
    "err": "lỗi",
    "loi": "lỗi",
    "acc": "tài khoản",
    "tai khoan": "tài khoản",
    "may tinh": "máy tính",
    "cham": "chậm",
    "lag": "lag",
    "qua troi": "nhiều",
    "nho": "nhớ",
    "vao": "vào",
    "ket noi": "kết nối",
    "wifi": "wifi",
    "wi-fi": "wifi",
}

EXACT_TECHNICAL_TERMS = {
    "forticlient", "cisco", "anyconnect", "bitlocker", "outlook", "exchange",
    "sap", "teams", "zoom", "autocad", "adobe", "workday", "hris", "gitlab",
    "github", "windows", "office", "word", "excel", "powerpoint", "azure",
    "okta", "pacs", "dicom", "his", "wms", "erp", "crm",
    "vpn", "mfa", "2fa", "sspr", "bsod", "dns", "dhcp", "lan", "wifi",
    "wireless", "ost", "pst", "ntfs", "pos", "mri", "x-quang",
    "stop code", "blue screen", "recovery key", "authentication failed",
    "maximum sessions exceeded", "session timeout", "outbox", "disconnected",
    "phishing", "malware", "ransomware", "403", "401", "500",
}


def normalize_informal_query(text: str) -> str:
    words = text.split()
    norm = []
    i = 0
    while i < len(words):
        if i + 1 < len(words):
            two = f"{words[i]} {words[i+1]}".lower()
            if two in INFORMAL_MAP:
                norm.append(INFORMAL_MAP[two])
                i += 2
                continue
        w = words[i].lower()
        if w in INFORMAL_MAP:
            norm.append(INFORMAL_MAP[w])
        else:
            norm.append(words[i])
        i += 1
    return " ".join(norm)


def extract_exact_technical_tokens(text: str) -> set[str]:
    text_lower = text.lower()
    found = set()
    for term in EXACT_TECHNICAL_TERMS:
        if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
            found.add(term)
    return found


class InvertedBM25Index:
    def __init__(self, doc_ids: list[str], documents: list[str], metadatas: list[dict]):
        self.doc_ids = doc_ids
        self.documents = documents
        self.metadatas = metadatas
        self.N = len(doc_ids)

        self.doc_tokens: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.df: Counter = Counter()

        for content, meta in zip(documents, metadatas):
            title = meta.get("title", "")
            tags = meta.get("tags", "")
            solution = meta.get("solution", "")
            searchable = f"{title} {title} {title} {tags} {tags} {solution} {content}"
            tokens = self._tokenize(searchable)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            for t in set(tokens):
                self.df[t] += 1

        self.avg_doc_len = sum(self.doc_lengths) / self.N if self.N else 1.0

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        norm = _normalize_search_text(text)
        tokens = re.findall(r"[^\W_]+", norm, flags=re.UNICODE)
        return [t for t in tokens if len(t) > 1]

    def search(
        self,
        query: str,
        top_n: int = 60,
        user_company_unit: str | None = None,
        user_department: str | None = None,
    ) -> dict[str, int]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return {}

        scores = [0.0] * self.N
        k1, b = 1.5, 0.75
        for t in q_tokens:
            if t not in self.df:
                continue
            n_t = self.df[t]
            idf = math.log((self.N - n_t + 0.5) / (n_t + 0.5) + 1.0)
            for i in range(self.N):
                f = self.doc_tokens[i].count(t)
                if f == 0:
                    continue
                tf = (f * (k1 + 1)) / (f + k1 * (1 - b + b * (self.doc_lengths[i] / self.avg_doc_len)))
                scores[i] += idf * tf

        candidates = []
        for i, s in enumerate(scores):
            if s <= 0.0:
                continue
            meta = self.metadatas[i]
            if not _metadata_allowed(meta, user_company_unit, user_department):
                continue
            if scan_indirect_injection(self.documents[i]):
                continue
            candidates.append((self.doc_ids[i], s))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(candidates[:top_n])}


def run_benchmark():
    col = get_collection()
    all_data = col.get(include=["metadatas", "documents"])
    doc_ids = all_data["ids"]
    documents = all_data["documents"]
    metadatas = all_data["metadatas"]
    bm25_index = InvertedBM25Index(doc_ids, documents, metadatas)

    golden_cases = json.load(open(ROOT_DIR / "eval" / "retrieval_golden_v1.json", encoding="utf-8"))["cases"]

    # Pre-embed queries to avoid memory churn
    query_embeddings = {}
    for c in golden_cases:
        q = c["query"]
        norm_q = normalize_informal_query(q)
        exp_q = _expand_query(norm_q if norm_q != q else q)
        query_embeddings[q] = embed_query(_expand_query(q))
        query_embeddings[norm_q] = embed_query(exp_q)
    gc.collect()

    # ─── EXPERIMENT A: Current Baseline ───────────────────────────────────────
    results_a = []
    t0 = time.perf_counter()
    for c in golden_cases:
        docs = search_similar(c["query"], n_results=5, user_company_unit=c.get("tenant"), user_department=c.get("department"))
        results_a.append(evaluate_single_case(c, docs, top_k=5))
    lat_a = (time.perf_counter() - t0) / len(golden_cases) * 1000
    sum_a = summarize_retrieval_evaluation(results_a)

    # ─── EXPERIMENT B: Normalization Only (Dense) ─────────────────────────────
    results_b = []
    t0 = time.perf_counter()
    for c in golden_cases:
        norm_q = normalize_informal_query(c["query"])
        docs = search_similar(norm_q, n_results=5, user_company_unit=c.get("tenant"), user_department=c.get("department"))
        results_b.append(evaluate_single_case(c, docs, top_k=5))
    lat_b = (time.perf_counter() - t0) / len(golden_cases) * 1000
    sum_b = summarize_retrieval_evaluation(results_b)

    # ─── EXPERIMENT C: Dense + BM25 RRF ───────────────────────────────────────
    def search_c(query: str, tenant=None, dept=None, n_results=5):
        norm_q = normalize_informal_query(query)
        q_emb = query_embeddings.get(norm_q) or embed_query(_expand_query(norm_q))
        dense_res = col.query(
            query_embeddings=[q_emb],
            n_results=min(max(n_results * 8, n_results), col.count() or 1),
            include=["documents", "metadatas", "distances"],
        )
        dense_ranks = {}
        dense_docs = {}
        if dense_res and dense_res.get("documents"):
            dense_rank = 1
            for i, doc in enumerate(dense_res["documents"][0]):
                meta = dense_res["metadatas"][0][i] if dense_res.get("metadatas") else {}
                if not _metadata_allowed(meta, tenant, dept) or scan_indirect_injection(doc):
                    continue
                did = dense_res["ids"][0][i]
                dist = dense_res["distances"][0][i]
                dense_ranks[did] = dense_rank
                dense_docs[did] = {"doc_id": did, "content": doc, "metadata": meta, "distance": dist, "semantic_score": max(0.0, 1.0 - dist)}
                dense_rank += 1

        bm25_ranks = bm25_index.search(norm_q, user_company_unit=tenant, user_department=dept)

        k = 60
        candidates = []
        for did in set(dense_ranks.keys()) | set(bm25_ranks.keys()):
            dense_r = dense_ranks.get(did)
            bm25_r = bm25_ranks.get(did)
            dense_rrf = 1.0 / (k + dense_r) if dense_r else 0.0
            bm25_rrf = 1.0 / (k + bm25_r) if bm25_r else 0.0

            if did in dense_docs:
                d_info = dense_docs[did]
            else:
                idx = doc_ids.index(did)
                d_info = {"doc_id": did, "content": documents[idx], "metadata": metadatas[idx], "distance": 1.0, "semantic_score": 0.0}

            fused_score = dense_rrf * 1.0 + bm25_rrf * 1.0
            d_info["relevance_score"] = fused_score
            candidates.append(d_info)

        candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        max_s = candidates[0]["relevance_score"] if candidates else 1.0
        for d in candidates:
            d["relevance_score"] = d["relevance_score"] / max_s if max_s > 0 else 0.0
        return candidates[:n_results]

    results_c = []
    t0 = time.perf_counter()
    for c in golden_cases:
        docs = search_c(c["query"], tenant=c.get("tenant"), dept=c.get("department"), n_results=5)
        results_c.append(evaluate_single_case(c, docs, top_k=5))
    lat_c = (time.perf_counter() - t0) / len(golden_cases) * 1000
    sum_c = summarize_retrieval_evaluation(results_c)

    # ─── EXPERIMENT D & E: Selected Configuration ─────────────────────────────
    def search_d(query: str, tenant=None, dept=None, n_results=5):
        norm_q = normalize_informal_query(query)
        exact_tokens = extract_exact_technical_tokens(query) | extract_exact_technical_tokens(norm_q)
        q_emb = query_embeddings.get(norm_q) or embed_query(_expand_query(norm_q))
        dense_res = col.query(
            query_embeddings=[q_emb],
            n_results=min(max(n_results * 8, n_results), col.count() or 1),
            include=["documents", "metadatas", "distances"],
        )
        dense_ranks = {}
        dense_docs = {}
        if dense_res and dense_res.get("documents"):
            dense_rank = 1
            for i, doc in enumerate(dense_res["documents"][0]):
                meta = dense_res["metadatas"][0][i] if dense_res.get("metadatas") else {}
                if not _metadata_allowed(meta, tenant, dept) or scan_indirect_injection(doc):
                    continue
                did = dense_res["ids"][0][i]
                dist = dense_res["distances"][0][i]
                dense_ranks[did] = dense_rank
                dense_docs[did] = {"doc_id": did, "content": doc, "metadata": meta, "distance": dist, "semantic_score": max(0.0, 1.0 - dist)}
                dense_rank += 1

        bm25_ranks = bm25_index.search(norm_q, user_company_unit=tenant, user_department=dept)

        k = 60
        candidates = []
        for did in set(dense_ranks.keys()) | set(bm25_ranks.keys()):
            dense_r = dense_ranks.get(did)
            bm25_r = bm25_ranks.get(did)
            dense_rrf = 1.0 / (k + dense_r) if dense_r else 0.0
            bm25_rrf = 1.0 / (k + bm25_r) if bm25_r else 0.0

            if did in dense_docs:
                d_info = dense_docs[did]
            else:
                idx = doc_ids.index(did)
                d_info = {"doc_id": did, "content": documents[idx], "metadata": metadatas[idx], "distance": 1.0, "semantic_score": 0.0}

            meta = d_info["metadata"]
            searchable_text = f"{meta.get('title', '')} {meta.get('tags', '')} {meta.get('solution', '')} {d_info.get('content', '')}".lower()

            exact_matches = sum(1 for token in exact_tokens if token in searchable_text)
            exact_boost = 0.005 * exact_matches

            source_type = meta.get("source", "")
            auth_factor = 1.10 if source_type == "internal_curated_kb" else 1.0

            fused_score = (dense_rrf * 1.0 + bm25_rrf * 1.2 + exact_boost) * auth_factor
            d_info["relevance_score"] = fused_score
            candidates.append(d_info)

        candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        max_s = candidates[0]["relevance_score"] if candidates else 1.0
        for d in candidates:
            d["relevance_score"] = d["relevance_score"] / max_s if max_s > 0 else 0.0
        return candidates[:n_results]

    results_d = []
    t0 = time.perf_counter()
    for c in golden_cases:
        docs = search_d(c["query"], tenant=c.get("tenant"), dept=c.get("department"), n_results=5)
        results_d.append(evaluate_single_case(c, docs, top_k=5))
    lat_d = (time.perf_counter() - t0) / len(golden_cases) * 1000
    sum_d = summarize_retrieval_evaluation(results_d)

    print("==========================================================================================")
    print(f"{'Metric':<18} | {'Baseline (A)':<14} | {'Norm Only (B)':<14} | {'Dense+BM25 (C)':<14} | {'Selected (D/E)':<14}")
    print("==========================================================================================")
    metrics_list = [
        ("HitRate@1", "hit_rate_at_1", True),
        ("Recall@1", "recall_at_1", True),
        ("HitRate@3", "hit_rate_at_3", True),
        ("Recall@3", "recall_at_3", True),
        ("HitRate@5", "hit_rate_at_5", True),
        ("Recall@5", "recall_at_5", True),
        ("MRR@5", "mrr_at_5", False),
        ("nDCG@5", "ndcg_at_5", False),
    ]
    for label, key, is_pct in metrics_list:
        va = f"{sum_a[key]:.1%}" if is_pct else f"{sum_a[key]:.4f}"
        vb = f"{sum_b[key]:.1%}" if is_pct else f"{sum_b[key]:.4f}"
        vc = f"{sum_c[key]:.1%}" if is_pct else f"{sum_c[key]:.4f}"
        vd = f"{sum_d[key]:.1%}" if is_pct else f"{sum_d[key]:.4f}"
        print(f"{label:<18} | {va:<14} | {vb:<14} | {vc:<14} | {vd:<14}")

    print("------------------------------------------------------------------------------------------")
    print(f"{'D_typo Hit@1':<18} | {sum_a['category_summary']['D_typo_informal']['hit_at_1']:.1%}          | {sum_b['category_summary']['D_typo_informal']['hit_at_1']:.1%}          | {sum_c['category_summary']['D_typo_informal']['hit_at_1']:.1%}          | {sum_d['category_summary']['D_typo_informal']['hit_at_1']:.1%}")
    print(f"{'B_exact Hit@1':<18} | {sum_a['category_summary']['B_exact_token']['hit_at_1']:.1%}          | {sum_b['category_summary']['B_exact_token']['hit_at_1']:.1%}          | {sum_c['category_summary']['B_exact_token']['hit_at_1']:.1%}          | {sum_d['category_summary']['B_exact_token']['hit_at_1']:.1%}")
    print(f"{'Cross-Tenant':<18} | {sum_a['cross_tenant_leak_count']:<14} | {sum_b['cross_tenant_leak_count']:<14} | {sum_c['cross_tenant_leak_count']:<14} | {sum_d['cross_tenant_leak_count']:<14}")
    print(f"{'Forbidden':<18} | {sum_a['forbidden_doc_retrieval_count']:<14} | {sum_b['forbidden_doc_retrieval_count']:<14} | {sum_c['forbidden_doc_retrieval_count']:<14} | {sum_d['forbidden_doc_retrieval_count']:<14}")
    print(f"{'Latency (ms)':<18} | {lat_a:<14.1f} | {lat_b:<14.1f} | {lat_c:<14.1f} | {lat_d:<14.1f}")
    print("==========================================================================================")


if __name__ == "__main__":
    run_benchmark()
