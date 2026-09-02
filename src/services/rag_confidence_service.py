"""
Dịch vụ tính RAG Confidence Score — Đánh giá chất lượng truy vấn RAG đa chiều.

Công thức: C_RAG = w1 * C_retrieval + w2 * C_consensus + w3 * C_groundedness

- C_retrieval:    Độ mạnh tương quan của tài liệu top-1 & phân cấp uy tín nguồn.
- C_consensus:    Độ đồng thuận giữa các kênh (Dense Vector vs BM25 Keyword ranking).
- C_groundedness: Độ trung thực/bám sát ngữ cảnh RAG của câu trả lời LLM (qua CrossEncoder).
                  Tự động fallback về 0.0 an toàn khi mô hình NLI gặp lỗi.

Trọng số w1, w2, w3 có thể cấu hình linh hoạt qua biến môi trường RAG_CONFIDENCE_W1/W2/W3 trong .env.
Cả 3 thành phần đều nằm trong khoảng [0.0, 1.0], do đó C_RAG luôn nằm trong khoảng chuẩn [0.0, 1.0].
"""
from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np

from src.config import get_settings

# Bảng hệ số uy tín nguồn tài liệu dành riêng cho C_retrieval (giá trị trong [0.0, 1.0]).
# Không dùng bảng từ rag_service vì bảng đó có giá trị > 1.0 (dùng để boost rerank),
# còn ở đây cần nhân trực tiếp vào retrieval_base nên phải giới hạn trong [0.0, 1.0].
SOURCE_AUTHORITY_FACTORS: dict[str, float] = {
    "internal_curated_kb":        1.00,  # Tier 1  — KB nội bộ chính thức / Runbook (cao nhất)
    "approved_internal_source":   0.95,  # Tier 1.5 — Chính sách nội bộ được phê duyệt
    "official_web_documentation": 0.85,  # Tier 2  — Tài liệu nhà cung cấp chính thức
    "historical_resolved_ticket": 0.75,  # Tier 3  — Ticket đã giải quyết trước đây
    "NO_SOURCE_KEY":              0.65,  # Tier 4  — Nguồn chưa phân loại / tự động KB
}

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache riêng cho NLI Groundedness model (TÁCH BIỆT khỏi reranker_service)
# Reranker dùng ms-marco (query↔doc relevance).
# Groundedness dùng NLI multilingual (answer↔doc entailment).
# ---------------------------------------------------------------------------
_nli_lock = threading.Lock()
_cached_nli_encoder: Any = None
_nli_load_attempted: bool = False


def _get_nli_encoder() -> Any:
    """Thread-safe lazy loader cho NLI CrossEncoder dùng để tính C_groundedness.

    Trả về model đã load hoặc None nếu load thất bại.
    Model được cache lại sau lần load đầu tiên.
    """
    global _cached_nli_encoder, _nli_load_attempted

    with _nli_lock:
        if _cached_nli_encoder is not None:
            return _cached_nli_encoder
        if _nli_load_attempted:
            return None

        _nli_load_attempted = True
        settings = get_settings()
        model_name = settings.groundedness_model_name
        max_length = settings.groundedness_model_max_length

        try:
            from sentence_transformers import CrossEncoder

            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"

            print(f"[NLI] Đang tải model groundedness: {model_name} | device={device} | max_length={max_length}")
            # Chiến lược load 2 bước: ưu tiên cache local (để offline / giảm latency).
            # Nếu chưa cache (OSError/EnvironmentError), fall-through sang download tự động.
            # Không dùng local_files_only=True cho toàn bộ session —
            # tránh trường hợp model có thể tải được nhưng bị block vĩnh viễn.
            try:
                _cached_nli_encoder = CrossEncoder(
                    model_name, max_length=max_length, device=device,
                    local_files_only=True,
                )
                print(f"[NLI] Load từ cache local: {model_name}")
            except OSError:
                logger.warning(
                    "[NLI] '%s' chưa có trong local cache. Tải từ Hugging Face Hub...",
                    model_name,
                )
                _cached_nli_encoder = CrossEncoder(
                    model_name, max_length=max_length, device=device,
                )
                print(f"[NLI] Tải từ Hub thành công: {model_name}")
            logger.info("Loaded NLI groundedness model: %s on %s", model_name, device)
        except Exception as exc:
            logger.warning(
                "Không thể load NLI model '%s' (local_files_only=True): %s. "
                "C_groundedness sẽ fallback về 0.0.",
                model_name, exc,
            )
            _cached_nli_encoder = None

        return _cached_nli_encoder


# ---------------------------------------------------------------------------
# Thành phần A: C_retrieval
# ---------------------------------------------------------------------------

def extract_retrieval_score(docs: list[dict[str, Any]]) -> float:
    """Tính C_retrieval trong khoảng [0.0, 1.0].

    Công thức:
        retrieval_base = 0.7 * S_top1 + 0.3 * min(1.0, margin * 2.0)
        C_retrieval    = retrieval_base * A_source

    Trong đó:
        S_top1   — Điểm tương quan relevance_score đã chuẩn hóa của tài liệu tốt nhất
        margin   — Khoảng cách điểm giữa top-1 và top-2 (bằng 0.0 nếu chỉ có 1 kết quả)
        A_source — Hệ số uy tín của nguồn tài liệu (giới hạn tối đa 1.0)
    """
    if not docs:
        return 0.0

    top1 = docs[0]
    s_top1 = float(top1.get("relevance_score", 0.0))
    s_top2 = float(docs[1].get("relevance_score", 0.0)) if len(docs) > 1 else 0.0
    margin = max(0.0, s_top1 - s_top2)

    source_type = top1.get("metadata", {}).get("source", "NO_SOURCE_KEY")
    auth_factor = SOURCE_AUTHORITY_FACTORS.get(source_type, 0.65)

    margin_component = min(1.0, margin * 2.0)
    retrieval_base = 0.7 * s_top1 + 0.3 * margin_component
    # retrieval_base ≤ 1.0 (tổng hợp lồi) và auth_factor ≤ 1.0 (bảng mới giới hạn sẵn)
    # → tích không bao giờ vượt 1.0, nên min(1.0, ...) là dư thừa; chỉ giữ max(0.0, ...) để phòng thủ.
    c_retrieval = round(max(0.0, retrieval_base * auth_factor), 3)

    logger.debug(
        "[C_Retrieval] docs=%d, s_top1=%.4f, s_top2=%.4f, margin=%.4f, source=%s, auth=%.4f -> C_retrieval=%.4f",
        len(docs), s_top1, s_top2, margin, source_type, auth_factor, c_retrieval,
    )

    return c_retrieval


# ---------------------------------------------------------------------------
# Thành phần B: C_consensus
# ---------------------------------------------------------------------------

def extract_consensus_score(top1_doc: dict[str, Any]) -> float:
    """Tính C_consensus nhận các giá trị {0.50, 0.75, 1.00}.

    Đo lường sự đồng thuận giữa kênh truy vấn Dense Vector và kênh BM25 Lexical
    đối với tài liệu đứng đầu.

    Các mức độ:
        1.00 — Tài liệu top-1 xuất hiện trong cả Top-3 Dense VÀ Top-3 BM25 (đồng thuận rất cao)
        0.75 — Tài liệu top-1 xuất hiện trong cả Top-5 Dense VÀ Top-5 BM25 (đồng thuận vừa)
        0.50 — Tài liệu top-1 chỉ xuất hiện ở 1 trong 2 kênh (đồng thuận thấp)
    """
    dense_rank = top1_doc.get("dense_rank")
    lexical_rank = top1_doc.get("lexical_rank")

    if dense_rank and lexical_rank:
        if dense_rank <= 3 and lexical_rank <= 3:
            return 1.00
        if dense_rank <= 5 and lexical_rank <= 5:
            return 0.75
    return 0.50


# ---------------------------------------------------------------------------
# Thành phần C: C_groundedness (Đánh giá độ trung thực qua mô hình NLI)
# ---------------------------------------------------------------------------

# Giới hạn ký tự trước khi truyền vào model.
# Tính toán dựa trên max_length=512 tokens của model:
#   - Tiếng Việt ≈ 3–4 ký tự/token với multilingual tokenizer
#   - Answer  600 ký tự ≈ 150–200 tokens
#   - Doc     900 ký tự ≈ 225–300 tokens
#   - Tổng    ≈ 375–500 tokens + [CLS]/[SEP] → vừa đủ trong 512 tokens
_ANSWER_MAX_CHARS = 600
_DOC_MAX_CHARS    = 900


def calculate_groundedness_with_reranker(
    answer: str,
    context_docs: list[dict[str, Any]],
) -> float:
    """Tính C_groundedness trong khoảng [0.0, 1.0] bằng NLI CrossEncoder đa ngôn ngữ.

    Dùng model NLI (multilingual-MiniLMv2-L6-mnli-xnli).
    Model NLI được train để phân loại quan hệ giữa 2 văn bản thành 3 nhãn:
        - Index 0: entailment   (câu trả lời được hỗ trợ bởi tài liệu KB)  ← dùng cái này
        - Index 1: neutral      (không liên quan)
        - Index 2: contradiction (mâu thuẫn)

    Cặp đầu vào: (doc_KB [premise], answer_LLM [hypothesis])
    Premise là KB vì ta muốn kiểm tra xem tài liệu KB có 'chứng minh' câu trả lời không.
    """
    if not answer or not context_docs:
        return 0.0

    try:
        encoder = _get_nli_encoder()
        if encoder is None:
            logger.debug("NLI model không khả dụng; fallback C_groundedness = 0.0")
            return 0.0

        # Cắt để vừa 512 token — xem hằng số _ANSWER_MAX_CHARS / _DOC_MAX_CHARS bên trên
        clean_answer = answer.strip()[:_ANSWER_MAX_CHARS]

        # Cặp: (premise=KB_doc, hypothesis=LLM_answer)
        # Thứ tự đúng: KB là "sự thật đã biết", answer là "giả thuyết cần kiểm chứng"
        pairs = []
        for doc in context_docs[:3]:
            doc_content = doc.get("content", "").strip()[:_DOC_MAX_CHARS]
            if doc_content:
                pairs.append((doc_content, clean_answer))

        if not pairs:
            return 0.0

        # Dùng apply_softmax=True — CrossEncoder tự chuẩn hóa, không cần viết softmax thủ công.
        # Đồng thời giữ raw logits riêng để hiển thị trong debug log.
        # Labels: {0: 'entailment', 1: 'neutral', 2: 'contradiction'}
        raw_logits = np.array(encoder.predict(pairs))
        probs       = np.array(encoder.predict(pairs, apply_softmax=True))

        # Đảm bảo luôn là 2D (n_pairs, 3) dù model trả về 1D khi chỉ có 1 cặp
        if raw_logits.ndim == 1:
            raw_logits = raw_logits.reshape(1, -1)
        if probs.ndim == 1:
            probs = probs.reshape(1, -1)

        entailment_probs = probs[:, 0]           # cột 0 = entailment
        max_entailment = float(entailment_probs.max())
        c_groundedness = round(max(0.0, min(1.0, max_entailment)), 3)

        logger.debug(
            "[C_Groundedness] model=%s, pairs=%d, answer_len=%d, max_entailment=%.4f -> C_groundedness=%.4f",
            getattr(encoder, "model_name_or_path", "NLI model"), len(pairs), len(clean_answer), max_entailment, c_groundedness,
        )

        return c_groundedness

    except Exception as exc:
        logger.warning(
            "Đánh giá Groundedness qua NLI thất bại; fallback C_groundedness = 0.0: %s",
            exc,
        )
        return 0.0


# ---------------------------------------------------------------------------
# Tổng hợp cuối cùng: C_RAG = w1 * C_retrieval + w2 * C_consensus + w3 * C_groundedness
# ---------------------------------------------------------------------------

def compute_final_rag_confidence(
    c_retrieval: float,
    c_consensus: float,
    c_groundedness: float,
) -> float:
    """Tổng hợp 3 thành phần thành điểm C_RAG chuẩn trong khoảng [0.0, 1.0].

    Các trọng số được nạp từ cấu hình runtime (tùy chỉnh qua file .env):
        RAG_CONFIDENCE_W1 (mặc định 0.4) — trọng số cho C_retrieval
        RAG_CONFIDENCE_W2 (mặc định 0.2) — trọng số cho C_consensus
        RAG_CONFIDENCE_W3 (mặc định 0.4) — trọng số cho C_groundedness

    Kết quả luôn nằm trong khoảng [0.0, 1.0] vì từng thành phần đã được giới hạn
    và tổng các trọng số tạo thành tổ hợp lồi (w1 + w2 + w3 = 1.0).
    """
    settings = get_settings()
    w1 = settings.rag_confidence_w1
    w2 = settings.rag_confidence_w2
    w3 = settings.rag_confidence_w3

    c_rag = w1 * c_retrieval + w2 * c_consensus + w3 * c_groundedness
    logger.debug(
        "[C_RAG Summary] C_retrieval=%.4f, C_consensus=%.4f, C_groundedness=%.4f -> C_RAG=%.4f",
        c_retrieval, c_consensus, c_groundedness, c_rag,
    )
    return round(max(0.0, min(1.0, c_rag)), 3)
