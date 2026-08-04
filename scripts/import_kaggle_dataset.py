"""
Script import dataset ticket từ file Kaggle CSV (data/helpdesk_tickets.csv).

Cách dùng:
    python scripts/import_kaggle_dataset.py --limit 100
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import AsyncSessionLocal, init_db
from src.models.ticket import Ticket, TicketStatus, TicketCategory, TicketPriority, TicketUrgency
from src.models.user import User, UserRole
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "access": TicketCategory.ACCESS_PERMISSION,
    "security": TicketCategory.SECURITY,
    "software": TicketCategory.SOFTWARE,
    "hardware": TicketCategory.HARDWARE,
    "network": TicketCategory.NETWORK,
}

PRIORITY_MAP = {
    "low": TicketPriority.LOW,
    "medium": TicketPriority.MEDIUM,
    "high": TicketPriority.HIGH,
    "critical": TicketPriority.CRITICAL,
}

STATUS_MAP = {
    "open": TicketStatus.OPEN,
    "in progress": TicketStatus.IN_PROGRESS,
    "pending": TicketStatus.PENDING_HITL,
    "resolved": TicketStatus.RESOLVED,
    "closed": TicketStatus.CLOSED,
    "on hold": TicketStatus.PENDING_HITL,
}


async def import_csv(csv_path: str, limit: int = 100):
    await init_db()

    file_path = Path(csv_path)
    if not file_path.exists():
        logger.error(f"File không tồn tại: {csv_path}")
        return

    logger.info(f"Đang đọc dataset từ {csv_path} (limit: {limit})...")

    imported = 0
    async with AsyncSessionLocal() as db:
        # Get count of existing KGL- tickets to start numbering
        existing_res = await db.execute(select(Ticket).where(Ticket.ticket_number.like("KGL-%")))
        existing_count = len(existing_res.scalars().all())

        # Get first employee user for submitter_id
        res = await db.execute(select(User).where(User.role == UserRole.EMPLOYEE))
        user = res.scalars().first()
        if not user:
            logger.error("Không tìm thấy user employee trong DB. Vui lòng khởi động backend để seed users trước.")
            return

        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if imported >= limit:
                    break

                raw_cat = row.get("Category", "").strip().lower()
                raw_pri = row.get("Priority", "").strip().lower()
                raw_status = row.get("Status", "").strip().lower()
                desc = row.get("Description", "").strip()
                subcat = row.get("Subcategory", "").strip()
                escalated = row.get("Escalated", "").strip().lower() == "true"

                cat = CATEGORY_MAP.get(raw_cat, TicketCategory.OTHER)
                pri = PRIORITY_MAP.get(raw_pri, TicketPriority.MEDIUM)
                status = STATUS_MAP.get(raw_status, TicketStatus.OPEN)

                title = f"[{raw_cat.upper()}] {subcat}" if subcat else f"Ticket #{row.get('Ticket_ID')}"

                ticket_num = f"KGL-{existing_count + imported + 1:05d}"

                ticket = Ticket(
                    ticket_number=ticket_num,
                    title=title,
                    description=desc,
                    category=cat,
                    priority=pri,
                    urgency=TicketUrgency.MEDIUM,
                    status=status,
                    submitter_id=user.id,
                    routing_target=row.get("Assigned_Team"),
                    sla_escalated=escalated,
                )

                db.add(ticket)
                imported += 1

        await db.commit()
        logger.info(f"✅ Đã import thành công {imported} tickets từ Kaggle dataset vào CSDL!")


def main():
    parser = argparse.ArgumentParser(description="Import Kaggle Helpdesk Dataset vào Help Desk AI DB")
    parser.add_argument("--csv", default="data/helpdesk_tickets.csv", help="Đường dẫn file CSV")
    parser.add_argument("--limit", type=int, default=100, help="Số lượng ticket cần import")
    args = parser.parse_args()

    asyncio.run(import_csv(args.csv, args.limit))


if __name__ == "__main__":
    main()
