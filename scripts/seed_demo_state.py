"""Deterministic & Idempotent Demo Data Seed Script for Project P-236.

Sets up clean demonstration state across all 4 roles:
- Demo users (employee1, tech1, manager1, admin, etc.)
- Fulfillment group memberships for tech1
- Sample Incidents across representative states (Open, Pending HITL, In Progress, Resolved)
- Sample Service Requests (Pending Approval, In Progress, Fulfilled)
- ChromaDB Knowledge Base verification
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select, delete

from src.database import AsyncSessionLocal, init_db
from src.main import _seed_demo_users, _seed_knowledge_base
from src.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus, TicketSupportMode, TicketUrgency
from src.models.ticket_message import TicketMessage, TicketMessageSender
from src.models.service_request import ServiceRequest, ServiceRequestStatus
from src.models.user import User
from src.services.rag_service import get_collection_count

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demo_seed")


async def seed_demo_incidents(db):
    """Seed clean, representative tickets for demo presentation."""
    employee = (await db.execute(select(User).where(User.username == "employee1"))).scalar_one_or_none()
    tech = (await db.execute(select(User).where(User.username == "tech1"))).scalar_one_or_none()
    if not employee:
        return

    now = datetime.now(timezone.utc)

    demo_tickets = [
        {
            "ticket_number": "INC-20260816-0001",
            "title": "VPN FortiClient báo lỗi 809 trên Windows 11",
            "description": "Khi kết nối VPN từ mạng nhà để truy cập ERP công ty thì báo lỗi 809 kết nối mạng giữa máy tính của bạn và máy chủ VPN không thể được thiết lập.",
            "category": TicketCategory.NETWORK,
            "priority": TicketPriority.MEDIUM,
            "urgency": TicketUrgency.MEDIUM,
            "status": TicketStatus.OPEN,
            "support_mode": TicketSupportMode.AI,
            "confidence_score": 0.88,
            "routing_target": "Network IT",
            "suggested_solution": "Kiểm tra NAT Traversal trong registry (HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\PolicyAgent\\AssumeUDPEncapsulationContextOnSendRule = 2) và khởi động lại dịch vụ IPsec Policy Agent.",
            "submitter_id": employee.id,
            "assignee_id": None,
            "created_at": now - timedelta(minutes=45),
        },
        {
            "ticket_number": "INC-20260816-0002",
            "title": "Cần cấp quyền root và reset mật khẩu database server Production",
            "description": "Hệ thống cơ sở dữ liệu chính của cổng thanh toán gặp sự cố quá tải kết nối, cần IT cấp quyền Admin và reset pass root để can thiệp khẩn cấp.",
            "category": TicketCategory.SECURITY,
            "priority": TicketPriority.CRITICAL,
            "urgency": TicketUrgency.HIGH,
            "status": TicketStatus.PENDING_HITL,
            "support_mode": TicketSupportMode.HUMAN,
            "confidence_score": 0.52,
            "routing_target": "Security IT",
            "suggested_solution": "Thao tác đặc quyền cao trên môi trường Production yêu cầu phê duyệt HITL từ IT Manager.",
            "submitter_id": employee.id,
            "assignee_id": None,
            "created_at": now - timedelta(minutes=30),
        },
        {
            "ticket_number": "INC-20260816-0003",
            "title": "Máy in văn phòng tầng 3 bị kẹt giấy và báo lỗi Offline",
            "description": "Máy in HP LaserJet tại khu vực làm việc tầng 3 không in được tài liệu hợp đồng, đèn báo đỏ và màn hình thông báo Paper Jam.",
            "category": TicketCategory.HARDWARE,
            "priority": TicketPriority.LOW,
            "urgency": TicketUrgency.LOW,
            "status": TicketStatus.IN_PROGRESS,
            "support_mode": TicketSupportMode.HUMAN,
            "confidence_score": 0.82,
            "routing_target": "Workplace IT",
            "suggested_solution": "Kỹ thuật viên đang kiểm tra khay cuốn giấy và khởi động lại Print Spooler.",
            "submitter_id": employee.id,
            "assignee_id": tech.id if tech else None,
            "created_at": now - timedelta(hours=2),
        },
        {
            "ticket_number": "INC-20260816-0004",
            "title": "Sửa lỗi tệp dữ liệu Outlook PST và OST",
            "description": "Hộp thư Outlook báo lỗi file dữ liệu bị hỏng không thể đồng bộ thư mới.",
            "category": TicketCategory.SOFTWARE,
            "priority": TicketPriority.MEDIUM,
            "urgency": TicketUrgency.LOW,
            "status": TicketStatus.RESOLVED,
            "support_mode": TicketSupportMode.AI,
            "confidence_score": 0.95,
            "routing_target": "Workplace IT",
            "suggested_solution": "Đã chạy công cụ SCANPST.EXE để sửa chữa cấu trúc thư mục dữ liệu Outlook.",
            "submitter_id": employee.id,
            "assignee_id": tech.id if tech else None,
            "created_at": now - timedelta(hours=5),
            "resolved_at": now - timedelta(hours=4),
        },
    ]

    for item in demo_tickets:
        existing = (await db.execute(select(Ticket).where(Ticket.ticket_number == item["ticket_number"]))).scalar_one_or_none()
        if not existing:
            ticket = Ticket(**item)
            db.add(ticket)
            await db.flush()

            # Add initial conversation message
            db.add(TicketMessage(
                ticket_id=ticket.id,
                sender_id=employee.id,
                sender_type=TicketMessageSender.USER,
                content=item["description"],
                created_at=item["created_at"],
            ))
            if item["suggested_solution"]:
                db.add(TicketMessage(
                    ticket_id=ticket.id,
                    sender_id=None,
                    sender_type=TicketMessageSender.AGENT,
                    content=f"AI Copilot đã tiếp nhận sự cố:\n{item['suggested_solution']}",
                    created_at=item["created_at"] + timedelta(seconds=10),
                ))

    await db.commit()
    logger.info("Seeded demo tickets successfully.")


async def seed_demo_service_requests(db):
    """Seed representative Service Requests for employee, manager, technician demos."""
    employee = (await db.execute(select(User).where(User.username == "employee1"))).scalar_one_or_none()
    tech = (await db.execute(select(User).where(User.username == "tech1"))).scalar_one_or_none()
    if not employee:
        return

    now = datetime.now(timezone.utc)

    demo_requests = [
        {
            "request_number": "REQ-20260816-DEMO01",
            "service_id": "laptop_provisioning",
            "service_name": "Xin laptop mới",
            "category": "hardware",
            "status": ServiceRequestStatus.PENDING_APPROVAL,
            "fulfillment_group": "Workplace IT",
            "approval_policy": "manager_approval",
            "risk_level": "medium",
            "sla_hours": 48,
            "form_data": json.dumps({"reason": "Cấp mới cho nhân sự mới", "model": "Dell Latitude 7440", "department": "Corporate"}),
            "submitter_id": employee.id,
            "created_at": now - timedelta(hours=1),
        },
        {
            "request_number": "REQ-20260816-DEMO02",
            "service_id": "vpn_access",
            "service_name": "Xin quyền VPN",
            "category": "access",
            "status": ServiceRequestStatus.IN_PROGRESS,
            "fulfillment_group": "Network IT",
            "approval_policy": "direct_approval",
            "risk_level": "low",
            "sla_hours": 8,
            "form_data": json.dumps({"reason": "Làm việc từ xa theo lịch công tác", "user_group": "VPN-Remote"}),
            "submitter_id": employee.id,
            "assignee_id": tech.id if tech else None,
            "assigned_at": now - timedelta(minutes=30),
            "created_at": now - timedelta(hours=3),
        },
        {
            "request_number": "REQ-20260816-DEMO03",
            "service_id": "software_install",
            "service_name": "Yêu cầu cài đặt phần mềm được phê duyệt",
            "category": "software",
            "status": ServiceRequestStatus.FULFILLED,
            "fulfillment_group": "Workplace IT",
            "approval_policy": "direct_approval",
            "risk_level": "low",
            "sla_hours": 4,
            "form_data": json.dumps({"software_name": "Docker Desktop & VS Code", "purpose": "Phát triển ứng dụng nội bộ"}),
            "submitter_id": employee.id,
            "assignee_id": tech.id if tech else None,
            "fulfilled_at": now - timedelta(hours=1),
            "fulfilled_by_id": tech.id if tech else None,
            "created_at": now - timedelta(hours=6),
        },
    ]

    for item in demo_requests:
        existing = (await db.execute(select(ServiceRequest).where(ServiceRequest.request_number == item["request_number"]))).scalar_one_or_none()
        if not existing:
            req = ServiceRequest(**item)
            db.add(req)

    await db.commit()
    logger.info("Seeded demo Service Requests successfully.")


async def main():
    logger.info("Starting demo environment reset & seed...")
    await init_db()
    async with AsyncSessionLocal() as db:
        await _seed_demo_users(db)
        await _seed_knowledge_base(db)
        await seed_demo_incidents(db)
        await seed_demo_service_requests(db)

    kb_count = get_collection_count()
    logger.info(f"Demo environment ready. ChromaDB has {kb_count} documents.")


if __name__ == "__main__":
    asyncio.run(main())
