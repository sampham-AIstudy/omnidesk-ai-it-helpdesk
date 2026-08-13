"""Creation and lookup logic for the Service Request lifecycle."""
from __future__ import annotations

import json
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.service_request import ServiceRequest, ServiceRequestStatus
from src.timezone import vietnam_now

SERVICE_POLICIES: dict[str, dict[str, object]] = {
    "Đặt lại mật khẩu": {"group": "Identity & Access", "approval": [], "sla": 1, "risk": "low"},
    "Xin laptop mới": {"group": "Workplace IT", "approval": ["manager"], "sla": 24, "risk": "low"},
    "Xin máy in": {"group": "Workplace IT", "approval": ["manager"], "sla": 24, "risk": "low"},
    "Xin thiết bị ngoại vi": {"group": "Workplace IT", "approval": ["manager"], "sla": 16, "risk": "low"},
    "Xin quyền VPN": {"group": "Network & Security", "approval": ["manager"], "sla": 4, "risk": "medium"},
    "Xin quyền Git repo": {"group": "Platform Engineering", "approval": ["repository_owner"], "sla": 2, "risk": "medium"},
    "Xin DB access": {"group": "Data Platform", "approval": ["manager", "data_owner"], "sla": 8, "risk": "high"},
    "Xin Microsoft 365 license": {"group": "Cloud Productivity", "approval": ["manager"], "sla": 8, "risk": "low"},
    "Yêu cầu cài đặt phần mềm được phê duyệt": {"group": "Workplace IT", "approval": [], "sla": 8, "risk": "low"},
    "Xin antivirus": {"group": "Endpoint Security", "approval": [], "sla": 8, "risk": "low"},
    "Mở khóa tài khoản": {"group": "Identity & Access", "approval": [], "sla": 1, "risk": "low"},
    "Xin email alias": {"group": "Cloud Productivity", "approval": ["manager"], "sla": 8, "risk": "low"},
    "Cập nhật tên hiển thị / email": {"group": "Identity & Access", "approval": ["hr_record"], "sla": 8, "risk": "low"},
    "Xin IP tĩnh": {"group": "Network Operations", "approval": [], "sla": 16, "risk": "low"},
    "Xin truy cập mạng nội bộ": {"group": "Network & Security", "approval": ["manager"], "sla": 8, "risk": "medium"},
    "Đăng ký Wi-Fi cho thiết bị mới": {"group": "Network Operations", "approval": [], "sla": 4, "risk": "low"},
    "Đăng ký mượn thiết bị tạm thời": {"group": "Workplace IT", "approval": ["manager"], "sla": 8, "risk": "low"},
    "Xin chuyển máy / bàn làm việc": {"group": "Workplace IT", "approval": [], "sla": 16, "risk": "low"},
    "Yêu cầu hỗ trợ thiết bị phòng họp": {"group": "Workplace IT", "approval": [], "sla": 4, "risk": "low"},
}

# The catalog is a server-owned contract.  Clients may suggest a category for
# navigation, but must never be able to alter the fulfillment route, approval
# chain, SLA, or category stored on the service request.
SERVICE_CATEGORIES: dict[str, str] = {
    "Đặt lại mật khẩu": "accounts",
    "Xin laptop mới": "hardware",
    "Xin máy in": "hardware",
    "Xin thiết bị ngoại vi": "hardware",
    "Xin quyền VPN": "access",
    "Xin quyền Git repo": "access",
    "Xin DB access": "access",
    "Xin Microsoft 365 license": "software",
    "Yêu cầu cài đặt phần mềm được phê duyệt": "software",
    "Xin antivirus": "software",
    "Mở khóa tài khoản": "accounts",
    "Xin email alias": "accounts",
    "Cập nhật tên hiển thị / email": "accounts",
    "Xin IP tĩnh": "network",
    "Xin truy cập mạng nội bộ": "network",
    "Đăng ký Wi-Fi cho thiết bị mới": "network",
    "Đăng ký mượn thiết bị tạm thời": "onboarding",
    "Xin chuyển máy / bàn làm việc": "onboarding",
    "Yêu cầu hỗ trợ thiết bị phòng họp": "onboarding",
}


def list_service_catalog() -> list[dict[str, object]]:
    """Return the authoritative catalog metadata safe for employee UI use."""
    return [
        {
            "service_name": name,
            "category": SERVICE_CATEGORIES[name],
            "fulfillment_group": str(policy["group"]),
            "approval_roles": list(policy["approval"]),
            "risk_level": str(policy["risk"]),
            "sla_hours": int(policy["sla"]),
        }
        for name, policy in SERVICE_POLICIES.items()
    ]


def _request_number() -> str:
    # 32 bits of entropy makes a unique-index collision practically impossible
    # while keeping the identifier short enough for the existing column.
    return f"REQ-{vietnam_now():%Y%m%d}-{secrets.token_hex(4).upper()}"


async def create_service_request(
    db: AsyncSession, *, service_name: str, category: str, form_data: dict[str, str], submitter_id: int
) -> ServiceRequest:
    policy = SERVICE_POLICIES.get(service_name)
    if not policy:
        raise ValueError("Dịch vụ không nằm trong Service Catalog.")
    canonical_category = SERVICE_CATEGORIES[service_name]
    approvals = list(policy["approval"])
    request = ServiceRequest(
        request_number=_request_number(), service_id=service_name.lower().replace(" ", "-"),
        service_name=service_name, category=canonical_category, submitter_id=submitter_id,
        fulfillment_group=str(policy["group"]), approval_policy=json.dumps(approvals),
        risk_level=str(policy["risk"]), sla_hours=int(policy["sla"]),
        status=ServiceRequestStatus.PENDING_APPROVAL if approvals else ServiceRequestStatus.SUBMITTED,
        form_data=json.dumps(form_data, ensure_ascii=False),
    )
    db.add(request)
    await db.flush()
    await db.refresh(request)
    return request


async def get_service_request(db: AsyncSession, request_number: str) -> ServiceRequest | None:
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.request_number == request_number))
    return result.scalar_one_or_none()


async def list_service_requests(db: AsyncSession, submitter_id: int) -> list[ServiceRequest]:
    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.submitter_id == submitter_id).order_by(ServiceRequest.created_at.desc())
    )
    return list(result.scalars())
