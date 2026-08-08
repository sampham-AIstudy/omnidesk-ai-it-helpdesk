"""
Classification Evaluation Script
Đo accuracy và F1 score của classifier node trên labeled dataset.

Chạy:
    python eval/classification_eval.py

Output:
    - Accuracy tổng thể
    - Precision / Recall / F1 theo từng category
    - Confusion matrix
    - Báo cáo chi tiết
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("MISTRAL_API_KEY", os.getenv("MISTRAL_API_KEY", "dummy-for-eval"))

# ─── Ground Truth Dataset ─────────────────────────────────────────────────────
# Format: (title, description, true_category, true_priority)
EVAL_DATASET: list[tuple[str, str, str, str]] = [
    # NETWORK
    ("VPN không kết nối được",
     "Không vào được VPN FortiClient, báo authentication failed khi đăng nhập",
     "network", "medium"),
    ("Mạng nội bộ bị mất kết nối",
     "Toàn bộ tầng 3 không vào được mạng, các máy đều báo limited connectivity",
     "network", "high"),
    ("Không truy cập được internet",
     "Từ sáng máy không vào được internet, nhưng mạng nội bộ vẫn bình thường",
     "network", "low"),
    ("Kết nối WiFi không ổn định",
     "WiFi văn phòng hay bị ngắt kết nối, phải reconnect nhiều lần trong ngày",
     "network", "low"),

    # SOFTWARE
    ("Office 365 bị lỗi khi mở",
     "Word và Excel báo lỗi 'not responding' khi mở file lớn hơn 10MB",
     "software", "medium"),
    ("Phần mềm kế toán không khởi động",
     "Phần mềm kế toán Misa báo lỗi 'License expired' từ đầu tháng",
     "software", "high"),
    ("Chrome bị lỗi sau update",
     "Sau khi Chrome tự cập nhật, một số trang web nội bộ không load được",
     "software", "low"),
    ("Zoom không bật được camera",
     "Khi họp Zoom, camera không nhận dù đã cắm thiết bị, thử nhiều lần vẫn không được",
     "software", "medium"),

    # HARDWARE
    ("Màn hình bị đen khi dùng",
     "Màn hình tự dưng bị đen khi đang làm việc, phải restart mới sáng lại",
     "hardware", "medium"),
    ("Bàn phím hỏng một số phím",
     "Các phím số từ 1-5 và phím Enter không nhấn được, đã thử USB keyboard vẫn không nhận",
     "hardware", "low"),
    ("Máy tính không khởi động được",
     "Bật máy chỉ nghe tiếng bíp, màn hình không hiện gì, đã thử nhiều lần",
     "hardware", "high"),
    ("Máy in hết mực",
     "Máy in tầng 2 báo hết mực màu đen, cần thay cartridge",
     "hardware", "low"),

    # ACCESS / PERMISSION
    ("Không mở được folder shared",
     "Folder chia sẻ của phòng kinh doanh không access được, báo 'Access denied'",
     "access_permission", "medium"),
    ("Cần cấp quyền admin",
     "Cần quyền admin để cài phần mềm diệt virus theo yêu cầu IT policy",
     "access_permission", "low"),
    ("Tài khoản bị khóa",
     "Tài khoản domain bị khóa sau 5 lần đăng nhập sai, cần reset",
     "access_permission", "medium"),

    # EMAIL
    ("Outlook không nhận được email",
     "Từ hôm qua không nhận được email từ bên ngoài, email nội bộ vẫn bình thường",
     "email", "medium"),
    ("Email bị trả về",
     "Gửi email ra ngoài bị bounce, báo 'Delivery failed: 550 Relay not permitted'",
     "email", "high"),
    ("Không gửi được file đính kèm lớn",
     "File báo cáo 25MB không gửi được qua email, Outlook báo lỗi attachment too large",
     "email", "low"),

    # ERP/SAP
    ("SAP không đăng nhập được",
     "Nhân viên kế toán không vào được SAP ERP, báo 'maximum number of sessions exceeded'",
     "erp_sap", "high"),
    ("Lỗi khi tạo Purchase Order trong SAP",
     "Khi tạo PO trong SAP, hệ thống báo lỗi 'Document not saved - Error in fiscal year determination'",
     "erp_sap", "high"),

    # SECURITY
    ("Nghi ngờ máy tính bị virus",
     "Máy tính tự mở nhiều tab quảng cáo, antivirus báo threat, dữ liệu có thể bị lộ",
     "security", "critical"),
    ("Nhận email lừa đảo (phishing)",
     "Nhận email giả mạo ngân hàng yêu cầu click link và nhập mật khẩu, đã click",
     "security", "critical"),
    ("Mất USB chứa dữ liệu quan trọng",
     "USB chứa báo cáo tài chính quý bị thất lạc, không biết ai lấy",
     "security", "high"),

    # HR SYSTEM
    ("Không truy cập được hệ thống chấm công",
     "Không đăng nhập được phần mềm HR, lịch sử chấm công không hiện",
     "hr_system", "medium"),

    # INFRASTRUCTURE
    ("Server phòng kế toán bị sập",
     "File server của phòng kế toán không truy cập được, ảnh hưởng toàn bộ dữ liệu",
     "infrastructure", "critical"),
]


# ─── Evaluation Logic ─────────────────────────────────────────────────────────

async def run_classifier_on_sample(
    title: str,
    description: str,
    idx: int,
) -> dict[str, Any]:
    """Chạy classifier node trên một sample."""
    from src.agents.nodes.classifier import classify_node

    state = {
        "ticket_id": idx,
        "ticket_number": f"EVAL-{idx:04d}",
        "title": title,
        "description": description,
        "company_unit": "corporate",
        "is_production_impact": False,
        "submitter_is_vip": False,
    }

    result = await classify_node(state)
    return result


def compute_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Tính precision, recall, F1 theo từng label (macro average)."""
    from collections import defaultdict

    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    for true, pred in zip(y_true, y_pred):
        if true == pred:
            tp[true] += 1
        else:
            fp[pred] += 1
            fn[true] += 1

    per_class: dict[str, dict] = {}
    for label in labels:
        precision = tp[label] / (tp[label] + fp[label]) if (tp[label] + fp[label]) > 0 else 0.0
        recall    = tp[label] / (tp[label] + fn[label]) if (tp[label] + fn[label]) > 0 else 0.0
        f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": fn[label] + tp[label]}

    macro_f1       = sum(m["f1"] for m in per_class.values()) / len(per_class)
    macro_precision = sum(m["precision"] for m in per_class.values()) / len(per_class)
    macro_recall   = sum(m["recall"] for m in per_class.values()) / len(per_class)

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / len(y_true) if y_true else 0.0

    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "correct": correct,
        "total": len(y_true),
    }


def print_report(metrics: dict, results: list[dict]) -> None:
    """In báo cáo kết quả."""
    print("\n" + "=" * 60)
    print("  HELP DESK AI — CLASSIFICATION EVALUATION REPORT")
    print("=" * 60)
    print(f"  Total samples : {metrics['total']}")
    print(f"  Correct       : {metrics['correct']}")
    print(f"  Accuracy      : {metrics['accuracy']:.1%}")
    print(f"  Macro F1      : {metrics['macro_f1']:.3f}")
    print(f"  Macro Prec.   : {metrics['macro_precision']:.3f}")
    print(f"  Macro Recall  : {metrics['macro_recall']:.3f}")
    print("-" * 60)
    print(f"  {'Category':<20} {'Prec':>6} {'Recall':>7} {'F1':>6} {'Support':>8}")
    print("-" * 60)
    for label, m in sorted(metrics["per_class"].items()):
        print(f"  {label:<20} {m['precision']:>6.3f} {m['recall']:>7.3f} {m['f1']:>6.3f} {m['support']:>8d}")
    print("-" * 60)

    print("\n  ERRORS:")
    errors = [r for r in results if r["predicted"] != r["true_category"]]
    if not errors:
        print("  ✅ No errors!")
    else:
        for e in errors:
            print(f"  ❌ #{e['idx']:>3} | true={e['true_category']:<20} pred={e['predicted']:<20} | conf={e['confidence']:.2f}")
            print(f"        \"{e['title'][:60]}\"")
    print("=" * 60)

    # Save JSON report
    report_path = Path(__file__).parent / "eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro_f1"],
            "macro_precision": metrics["macro_precision"],
            "macro_recall": metrics["macro_recall"],
            "per_class": metrics["per_class"],
            "errors": errors,
            "total": metrics["total"],
            "correct": metrics["correct"],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  📄 Report saved to: {report_path}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run classification evaluation")
    parser.add_argument("--benchmark", default=None, help="Path to custom benchmark JSON")
    parser.add_argument("--limit", type=int, default=None, help="Limit sample count")
    args = parser.parse_args()

    dataset = EVAL_DATASET
    if args.benchmark and Path(args.benchmark).exists():
        print(f"📄 Loading benchmark from {args.benchmark}...")
        with open(args.benchmark, encoding="utf-8") as f:
            raw_data = json.load(f)
            dataset = [
                (item["title"], item["description"], item["true_category"], item.get("true_priority", "medium"))
                for item in raw_data
            ]

    if args.limit:
        dataset = dataset[:args.limit]

    print("🚀 Starting classification evaluation...")
    print(f"   Dataset size: {len(dataset)} samples")
    print("   LLM: Mistral API (real calls)\n")

    y_true: list[str] = []
    y_pred: list[str] = []
    results: list[dict] = []

    for idx, (title, description, true_cat, true_priority) in enumerate(dataset, 1):
        print(f"  [{idx:2d}/{len(dataset)}] {title[:50]}...")
        try:
            result = await run_classifier_on_sample(title, description, idx)
            predicted = result.get("category", "other")
            confidence = result.get("confidence_score", 0.0)
            error = result.get("error")

            if error:
                print(f"         ⚠️  Error: {error}")
                predicted = "other"
                confidence = 0.0

            status = "✅" if predicted == true_cat else "❌"
            print(f"         {status} true={true_cat:<20} pred={predicted:<20} conf={confidence:.2f}")

            y_true.append(true_cat)
            y_pred.append(predicted)
            results.append({
                "idx": idx,
                "title": title,
                "true_category": true_cat,
                "predicted": predicted,
                "confidence": confidence,
                "error": error,
            })

        except Exception as e:
            print(f"         ❌ Exception: {e}")
            y_true.append(true_cat)
            y_pred.append("other")
            results.append({"idx": idx, "title": title, "true_category": true_cat, "predicted": "other", "confidence": 0.0, "error": str(e)})

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.3)

    # Compute metrics
    all_labels = list(set(y_true))
    metrics = compute_metrics(y_true, y_pred, all_labels)
    print_report(metrics, results)


if __name__ == "__main__":
    asyncio.run(main())

