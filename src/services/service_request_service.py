"""Creation and lookup logic for the Service Request lifecycle."""
from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditAction, AuditLog
from src.models.service_request import ServiceRequest, ServiceRequestStatus
from src.models.technician_fulfillment_group import TechnicianFulfillmentGroup
from src.models.user import User
from src.services import auth_service
from src.timezone import vietnam_now


class ServiceRequestConflictError(Exception):
    """A deterministic state or exclusive-assignment conflict."""


class ServiceRequestAuthorizationError(Exception):
    """The caller is authenticated but cannot fulfill this routed request."""

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


def canonical_fulfillment_groups() -> list[str]:
    """The catalog policy is the single source of truth for valid group names."""
    return sorted({str(policy["group"]) for policy in SERVICE_POLICIES.values()})


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
    await write_service_request_audit(
        db, request=request, actor_id=submitter_id, action=AuditAction.SERVICE_REQUEST_CREATED,
        description="Service Request submitted",
        metadata={"new_status": request.status.value, "fulfillment_group": request.fulfillment_group},
        actor_type="user",
    )
    if approvals:
        await write_service_request_audit(
            db, request=request, actor_id=submitter_id, action=AuditAction.SERVICE_REQUEST_APPROVAL_REQUIRED,
            description="Service Request requires approval before fulfillment",
            metadata={"old_status": None, "new_status": request.status.value, "approval_roles": approvals},
            actor_type="user",
        )
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


async def list_technician_queue(
    db: AsyncSession, technician: User, *, fulfillment_group: str | None = None, limit: int = 100
) -> list[ServiceRequest]:
    """Return only tenant-scoped requests in the technician's explicit groups."""
    query = (
        select(ServiceRequest)
        .join(User, ServiceRequest.submitter_id == User.id)
        .where(ServiceRequest.status.in_([
            ServiceRequestStatus.SUBMITTED,
            ServiceRequestStatus.ASSIGNED,
            ServiceRequestStatus.IN_PROGRESS,
            ServiceRequestStatus.WAITING_FOR_USER,
        ]))
    )
    # ADMIN has always been an explicitly authorized fulfillment role in the
    # existing RBAC contract.  Explicit group membership governs technicians.
    if technician.role.value == "technician":
        membership = exists(
            select(TechnicianFulfillmentGroup.id).where(
                TechnicianFulfillmentGroup.technician_id == technician.id,
                TechnicianFulfillmentGroup.fulfillment_group == ServiceRequest.fulfillment_group,
            )
        )
        query = query.where(membership)
    tenant = auth_service.scoped_company_unit(technician)
    if tenant is not None:
        query = query.where(User.company_unit == tenant)
    if fulfillment_group:
        query = query.where(ServiceRequest.fulfillment_group == fulfillment_group)
    result = await db.execute(query.order_by(ServiceRequest.created_at.asc(), ServiceRequest.id.asc()).limit(limit))
    return list(result.scalars())


async def list_pending_service_request_approvals(
    db: AsyncSession, approver: User, *, limit: int = 100
) -> list[ServiceRequest]:
    """Manager/admin approval queue with the same central tenant boundary as other workflows."""
    query = (
        select(ServiceRequest)
        .join(User, ServiceRequest.submitter_id == User.id)
        .where(ServiceRequest.status == ServiceRequestStatus.PENDING_APPROVAL)
    )
    tenant = auth_service.scoped_company_unit(approver)
    if tenant is not None:
        query = query.where(User.company_unit == tenant)
    result = await db.execute(query.order_by(ServiceRequest.created_at.asc(), ServiceRequest.id.asc()).limit(limit))
    return list(result.scalars())


async def write_service_request_audit(
    db: AsyncSession,
    *,
    request: ServiceRequest,
    actor_id: int | None,
    action: AuditAction,
    description: str,
    metadata: dict[str, object],
    actor_type: str = "technician",
) -> AuditLog:
    submitter = await db.get(User, request.submitter_id)
    audit_metadata = {
        "request_number": request.request_number,
        "tenant": submitter.company_unit.value if submitter else None,
        **metadata,
    }
    log = AuditLog(
        service_request_id=request.id,
        actor_id=actor_id,
        actor_type=actor_type if actor_id else "system",
        action=action,
        description=description,
        # No form data is recorded here: it can contain sensitive request input.
        metadata_json=json.dumps(audit_metadata, ensure_ascii=False),
    )
    db.add(log)
    await db.flush()
    return log


async def take_service_request(db: AsyncSession, *, request: ServiceRequest, technician: User) -> ServiceRequest:
    """Atomically claim an unassigned submitted request, avoiding double takeover."""
    if request.status == ServiceRequestStatus.ASSIGNED and request.assignee_id == technician.id:
        return request  # naturally idempotent retry; no second audit event
    if request.status != ServiceRequestStatus.SUBMITTED or request.assignee_id is not None:
        raise ServiceRequestConflictError("Service Request is no longer available for takeover.")

    membership = None
    if technician.role.value == "technician":
        membership = exists(
            select(TechnicianFulfillmentGroup.id).where(
                TechnicianFulfillmentGroup.technician_id == technician.id,
                TechnicianFulfillmentGroup.fulfillment_group == request.fulfillment_group,
            )
        )
        if not await db.scalar(select(membership)):
            raise ServiceRequestAuthorizationError("You are not eligible for this fulfillment group.")

    claimed_at = datetime.now(UTC)
    result = await db.execute(
        update(ServiceRequest)
        .where(
            ServiceRequest.id == request.id,
            ServiceRequest.status == ServiceRequestStatus.SUBMITTED,
            ServiceRequest.assignee_id.is_(None),
            *([membership] if membership is not None else []),
        )
        .values(
            assignee_id=technician.id,
            assigned_at=claimed_at,
            status=ServiceRequestStatus.ASSIGNED,
            updated_at=claimed_at,
        )
    )
    if result.rowcount != 1:
        # A membership removal that races this update must remain a denial,
        # never a stale-client bypass.
        if membership is not None and not await db.scalar(select(membership)):
            raise ServiceRequestAuthorizationError("You are not eligible for this fulfillment group.")
        raise ServiceRequestConflictError("Service Request was claimed by another technician.")
    await db.refresh(request)
    await write_service_request_audit(
        db, request=request, actor_id=technician.id, action=AuditAction.SERVICE_REQUEST_ASSIGNED,
        description="Service Request taken by technician",
        metadata={"old_status": ServiceRequestStatus.SUBMITTED.value, "new_status": request.status.value},
    )
    return request


_TECHNICIAN_TRANSITIONS: dict[ServiceRequestStatus, set[ServiceRequestStatus]] = {
    ServiceRequestStatus.ASSIGNED: {ServiceRequestStatus.IN_PROGRESS},
    ServiceRequestStatus.IN_PROGRESS: {ServiceRequestStatus.WAITING_FOR_USER, ServiceRequestStatus.FULFILLED},
    ServiceRequestStatus.WAITING_FOR_USER: {ServiceRequestStatus.IN_PROGRESS},
}


async def transition_service_request(
    db: AsyncSession, *, request: ServiceRequest, technician: User, target: ServiceRequestStatus
) -> ServiceRequest:
    """Apply the canonical, persisted Service Request fulfillment state machine."""
    if request.assignee_id != technician.id:
        raise ServiceRequestConflictError("Only the assigned technician can update this Service Request.")
    if request.status == target:
        return request  # safe retry after a completed request/response exchange
    if target not in _TECHNICIAN_TRANSITIONS.get(request.status, set()):
        raise ServiceRequestConflictError("This Service Request transition is not allowed.")

    prior = request.status
    changed_at = datetime.now(UTC)
    values: dict[str, object] = {"status": target, "updated_at": changed_at}
    if target == ServiceRequestStatus.FULFILLED:
        values.update({"fulfilled_at": changed_at, "fulfilled_by_id": technician.id})
    result = await db.execute(
        update(ServiceRequest)
        .where(
            ServiceRequest.id == request.id,
            ServiceRequest.status == prior,
            ServiceRequest.assignee_id == technician.id,
        )
        .values(**values)
    )
    if result.rowcount != 1:
        raise ServiceRequestConflictError("Service Request changed before this update could be applied.")
    await db.refresh(request)
    await write_service_request_audit(
        db, request=request, actor_id=technician.id,
        action=AuditAction.SERVICE_REQUEST_FULFILLED if target == ServiceRequestStatus.FULFILLED else AuditAction.SERVICE_REQUEST_STATUS_CHANGED,
        description="Service Request fulfilled" if target == ServiceRequestStatus.FULFILLED else "Service Request status changed",
        metadata={"old_status": prior.value, "new_status": target.value},
    )
    await db.refresh(request)
    return request


async def approve_service_request(
    db: AsyncSession, *, request: ServiceRequest, approver: User, comment: str | None
) -> ServiceRequest:
    """Persist approval then return the request to the existing submitted queue state."""
    if request.status != ServiceRequestStatus.PENDING_APPROVAL:
        raise ServiceRequestConflictError("This Service Request is no longer awaiting approval.")
    decided_at = datetime.now(UTC)
    result = await db.execute(
        update(ServiceRequest)
        .where(ServiceRequest.id == request.id, ServiceRequest.status == ServiceRequestStatus.PENDING_APPROVAL)
        .values(
            status=ServiceRequestStatus.SUBMITTED,
            approved_by_id=approver.id,
            approved_at=decided_at,
            approval_comment=comment.strip() if comment else None,
            updated_at=decided_at,
        )
    )
    if result.rowcount != 1:
        raise ServiceRequestConflictError("Service Request was already decided by another manager.")
    await db.refresh(request)
    await write_service_request_audit(
        db, request=request, actor_id=approver.id, actor_type="manager",
        action=AuditAction.SERVICE_REQUEST_APPROVED,
        description="Service Request approved for fulfillment",
        metadata={"old_status": ServiceRequestStatus.PENDING_APPROVAL.value, "new_status": request.status.value},
    )
    return request


async def reject_service_request(
    db: AsyncSession, *, request: ServiceRequest, approver: User, reason: str
) -> ServiceRequest:
    """Persist a terminal rejection; a rejected request cannot enter fulfillment."""
    if request.status != ServiceRequestStatus.PENDING_APPROVAL:
        raise ServiceRequestConflictError("This Service Request is no longer awaiting approval.")
    decided_at = datetime.now(UTC)
    safe_reason = reason.strip()
    result = await db.execute(
        update(ServiceRequest)
        .where(ServiceRequest.id == request.id, ServiceRequest.status == ServiceRequestStatus.PENDING_APPROVAL)
        .values(
            status=ServiceRequestStatus.REJECTED,
            rejected_by_id=approver.id,
            rejected_at=decided_at,
            rejection_reason=safe_reason,
            updated_at=decided_at,
        )
    )
    if result.rowcount != 1:
        raise ServiceRequestConflictError("Service Request was already decided by another manager.")
    await db.refresh(request)
    await write_service_request_audit(
        db, request=request, actor_id=approver.id, actor_type="manager",
        action=AuditAction.SERVICE_REQUEST_REJECTED,
        description="Service Request rejected",
        metadata={
            "old_status": ServiceRequestStatus.PENDING_APPROVAL.value,
            "new_status": request.status.value,
            "reason": safe_reason,
        },
    )
    return request


async def service_request_activity(db: AsyncSession, request_id: int) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog).where(AuditLog.service_request_id == request_id).order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    )
    return list(result.scalars())


async def serialize_service_request(db: AsyncSession, request: ServiceRequest, *, include_activity: bool = False) -> dict[str, object]:
    """Produce a response from persisted state, without leaking form data to logs."""
    payload = {
        column.name: getattr(request, column.name)
        for column in ServiceRequest.__table__.columns
    }
    submitter = await db.get(User, request.submitter_id)
    assignee = await db.get(User, request.assignee_id) if request.assignee_id else None
    payload["requester_name"] = submitter.full_name if submitter else None
    payload["assignee_name"] = assignee.full_name if assignee else None
    if include_activity:
        activity = await service_request_activity(db, request.id)
        actor_ids = {entry.actor_id for entry in activity if entry.actor_id}
        actors = {
            actor.id: actor.full_name
            for actor in (await db.execute(select(User).where(User.id.in_(actor_ids)))).scalars()
        } if actor_ids else {}
        payload["activity"] = [
            {
                "action": entry.action,
                "actor_id": entry.actor_id,
                "actor_name": actors.get(entry.actor_id),
                "description": entry.description,
                "metadata_json": entry.metadata_json,
                "created_at": entry.created_at,
            }
            for entry in activity
        ]
    return payload
