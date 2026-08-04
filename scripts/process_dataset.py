"""
Python script xử lý dataset Kaggle (data/helpdesk_tickets.csv):
1. EDA & Thống kê dữ liệu
2. Trích xuất 500 mẫu benchmark cân bằng -> data/benchmark_kaggle_500.json
3. Trích xuất 200 bài học lịch sử -> data/historical_ticket_memory.json

Cách chạy:
    python scripts/process_dataset.py
"""
import json
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    'Access': 'access_permission',
    'Security': 'security',
    'Software': 'software',
    'Hardware': 'hardware',
    'Network': 'network'
}

PRIORITY_MAP = {
    'Low': 'low',
    'Medium': 'medium',
    'High': 'high',
    'Critical': 'critical'
}


def process_dataset(csv_path: str = "data/helpdesk_tickets.csv"):
    path = Path(csv_path)
    if not path.exists():
        logger.error(f"File không tồn tại: {csv_path}")
        return

    logger.info(f"Đang nạp dữ liệu từ {csv_path}...")
    df = pd.read_csv(path, nrows=50000)
    logger.info(f"✅ Đã nạp mẫu 50,000 dòng. Cột: {list(df.columns)}")

    # 1. Clean & Map
    clean_df = df.copy()
    clean_df['sys_category'] = clean_df['Category'].map(CATEGORY_MAP).fillna('other')
    clean_df['sys_priority'] = clean_df['Priority'].map(PRIORITY_MAP).fillna('medium')
    clean_df['title'] = clean_df.apply(
        lambda r: f"[{r['Category']}] {r['Subcategory']}" if pd.notna(r['Subcategory']) else f"Ticket #{r['Ticket_ID']}",
        axis=1
    )

    # 2. Extract 500 Benchmark Samples
    benchmark_samples = []
    for cat in clean_df['sys_category'].unique():
        cat_df = clean_df[clean_df['sys_category'] == cat]
        sample_size = min(100, len(cat_df))
        benchmark_samples.append(cat_df.sample(n=sample_size, random_state=42))

    benchmark_df = pd.concat(benchmark_samples).reset_index(drop=True)
    logger.info(f"📊 Trích xuất {len(benchmark_df)} mẫu benchmark cân bằng...")

    benchmark_records = []
    for _, r in benchmark_df.iterrows():
        benchmark_records.append({
            "ticket_id": int(r["Ticket_ID"]),
            "title": r["title"],
            "description": r["Description"],
            "true_category": r["sys_category"],
            "true_priority": r["sys_priority"],
            "assigned_team": r["Assigned_Team"],
            "is_escalated": bool(r["Escalated"])
        })

    benchmark_out = Path("data/benchmark_kaggle_500.json")
    with open(benchmark_out, "w", encoding="utf-8") as f:
        json.dump(benchmark_records, f, ensure_ascii=False, indent=2)
    logger.info(f"📄 Đã lưu file Benchmark tại: {benchmark_out.resolve()}")

    # 3. Extract Historical Memory Entries
    resolved_df = clean_df[clean_df['Status'] == 'Resolved'].head(200)
    memory_entries = []
    for _, r in resolved_df.iterrows():
        memory_entries.append({
            "doc_id": f"mem-kgl-{r['Ticket_ID']}",
            "title": r['title'],
            "content": f"Sự cố: {r['Description']}. Phân loại: {r['sys_category']}. Nhóm xử lý: {r['Assigned_Team']}. Thời gian giải quyết: {r['Resolution_Time_Hrs']} giờ.",
            "category": r['sys_category'],
            "solution": f"Đã được giải quyết bởi nhóm {r['Assigned_Team']} trong {r['Resolution_Time_Hrs']} giờ.",
        })

    memory_out = Path("data/historical_ticket_memory.json")
    with open(memory_out, "w", encoding="utf-8") as f:
        json.dump(memory_entries, f, ensure_ascii=False, indent=2)
    logger.info(f"🧠 Đã lưu file Memory tại: {memory_out.resolve()}")


if __name__ == "__main__":
    process_dataset()
