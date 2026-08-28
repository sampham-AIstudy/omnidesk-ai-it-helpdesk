"""
Script nạp 200 Historical Ticket Memories từ Kaggle vào ChromaDB Vector Store.

Cách dùng:
    python scripts/seed_historical_memory.py
"""
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.rag_service import get_collection_count, index_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_memories(json_path: str = "data/historical_ticket_memory.json"):
    path = Path(json_path)
    if not path.exists():
        logger.error(f"File không tồn tại: {json_path}. Vui lòng chạy notebooks/data_processing.ipynb trước.")
        return

    with open(path, encoding="utf-8") as f:
        memories = json.load(f)

    logger.info(f"Đang nạp {len(memories)} historical memories vào ChromaDB Vector Store...")

    indexed = 0
    for item in memories:
        doc_id = item.get("doc_id", f"mem-{indexed}")
        content = f"SỰ CỐ LỊCH SỬ: {item['title']}\n{item['content']}\nGIẢI PHÁP ĐÃ XỬ LÝ: {item.get('solution', '')}"
        metadata = {
            "title": item.get("title", "Sự cố lịch sử"),
            "category": item.get("category", "general"),
            "source": "Historical Resolved Ticket",
            "solution": item.get("solution", ""),
        }
        index_document(doc_id=doc_id, content=content, metadata=metadata)
        indexed += 1

    total_kb = get_collection_count()
    logger.info(f"✅ Đã nạp thành công {indexed} bài học lịch sử! Tổng tài liệu RAG trong ChromaDB: {total_kb}")


if __name__ == "__main__":
    seed_memories()
