"""Pydantic schemas — Request/Response models cho API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.models.audit_log import AuditAction
from src.models.service_request import ServiceRequestStatus
from src.models.ticket import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
    TicketSupportMode,
    TicketUrgency,
)
from src.models.ticket_message import TicketMessageSender
from src.models.user import CompanyUnit, UserRole

# ─── Auth Schemas ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    phone: str | None = None
    role: UserRole
    company_unit: CompanyUnit
    department: str | None
    is_vip: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=100, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=72)
    role: UserRole = UserRole.EMPLOYEE
    company_unit: CompanyUnit = CompanyUnit.CORPORATE
    department: str | None = None
    is_vip: bool = False


class UserSelfUpdate(BaseModel):
    """Fields an authenticated person may change on their own profile only."""
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: str | None = Field(None, min_length=5, max_length=100, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str | None = Field(None, max_length=30, pattern=r"^[0-9+().\-\s]*$")


class AdminUserUpdate(BaseModel):
    """Explicit allow-list for admin lifecycle changes; passwords stay separate."""
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: str | None = Field(None, min_length=5, max_length=100, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str | None = Field(None, max_length=30, pattern=r"^[0-9+().\-\s]*$")
    role: UserRole | None = None
    company_unit: CompanyUnit | None = None
    department: str | None = Field(None, max_length=100)
    is_vip: bool | None = None
    is_active: bool | None = None


class FulfillmentGroupListResponse(BaseModel):
    """Fixed, catalog-derived fulfillment groups; these are not dynamic entities."""

    items: list[str]


class TechnicianFulfillmentGroupsUpdate(BaseModel):
    """Replace a technician's explicit eligibility set; unknown groups are rejected server-side."""
    model_config = ConfigDict(extra="forbid")

    fulfillment_groups: list[str] = Field(default_factory=list, max_length=50)


class TechnicianFulfillmentGroupsResponse(BaseModel):
    technician_id: int
    fulfillment_groups: list[str]


# ─── Ticket Schemas ──────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    is_production_impact: bool = False
    duplicate_decision: Literal["create_anyway"] | None = None
    duplicate_of_ticket_id: int | None = None


class DuplicateCheckRequest(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)


class DuplicateTicketCandidate(BaseModel):
    ticket_id: int
    ticket_number: str
    title: str
    status: TicketStatus
    resolved_at: datetime | None = None
    solution: str | None = None
    classification: str
    score: float
    detection_method: str
    is_active: bool
    is_resolved: bool


class DuplicateCheckResponse(BaseModel):
    classification: str
    requires_confirmation: bool
    message: str | None = None
    matches: list[DuplicateTicketCandidate] = Field(default_factory=list)
    same_user_repeat_count: int = 0
    shared_incident_signal: bool = False


class DuplicateActionRequest(BaseModel):
    matched_ticket_id: int
    action: Literal["resolved_existing", "false_positive"]


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    category: TicketCategory | None
    priority: TicketPriority | None
    urgency: TicketUrgency | None
    confidence_score: float | None
    retrieval_confidence: float | None = None
    groundedness_score: float | None = None
    suggested_solution: str | None
    rag_sources: str | None
    agent_reasoning: str | None
    routing_target: str | None
    is_production_impact: bool
    status: TicketStatus
    hitl_required: bool
    hitl_note: str | None
    hitl_decided_at: datetime | None
    support_mode: TicketSupportMode = TicketSupportMode.AI
    closed_by: str | None = None
    resolution_summary: str | None = None
    rating: int | None = None
    rating_feedback: str | None = None
    duplicate_of_ticket_id: int | None = None
    duplicate_score: float | None = None
    duplicate_detection_method: str | None = None
    duplicate_confirmed_by: str | None = None
    parent_incident_ticket_id: int | None = None
    submitter_id: int
    submitter: UserResponse | None = None
    created_by_user: UserResponse | None = Field(default=None, validation_alias="submitter")
    assignee_id: int | None = None
    assignee: UserResponse | None = None
    sla_deadline: datetime | None
    sla_warning_sent: bool
    sla_escalated: bool
    first_response_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None = None
    reopened_at: datetime | None = None
    is_pinned: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    page: int
    page_size: int


class TicketPinRequest(BaseModel):
    pinned: bool = True
    reason: str | None = Field(default=None, max_length=255)


class HITLDecisionRequest(BaseModel):
    approved: bool
    note: str | None = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    note: str | None = None


class TicketEscalateRequest(BaseModel):
    reason: str = Field(default="Chuyên viên kỹ thuật yêu cầu leo thang xử lý lên cấp Quản lý.", min_length=3, max_length=500)
    escalate_to: str = Field(default="manager", max_length=50)
    bump_priority: bool = False
    handover_notes: str | None = Field(default=None, max_length=2000)


class TicketReopenRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class TicketRatingRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback: str | None = Field(None, max_length=2000)


class TicketMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    is_internal: bool = False


# ─── Service Request Schemas ──────────────────────────────────────────────────

class ServiceRequestCreate(BaseModel):
    service_name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=50)
    form_data: dict[str, str] = Field(default_factory=dict)


class ServiceCatalogItem(BaseModel):
    service_name: str
    category: str
    fulfillment_group: str
    approval_roles: list[str]
    risk_level: str
    sla_hours: int


class ServiceCatalogResponse(BaseModel):
    items: list[ServiceCatalogItem]


class ServiceRequestResponse(BaseModel):
    id: int
    request_number: str
    service_id: str
    service_name: str
    category: str
    status: ServiceRequestStatus
    fulfillment_group: str
    approval_policy: str
    risk_level: str
    sla_hours: int
    form_data: str
    rejection_reason: str | None
    approval_comment: str | None = None
    submitter_id: int
    requested_for_id: int | None
    approved_by_id: int | None = None
    approved_at: datetime | None = None
    rejected_by_id: int | None = None
    rejected_at: datetime | None = None
    assignee_id: int | None = None
    assigned_at: datetime | None = None
    fulfilled_at: datetime | None = None
    fulfilled_by_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServiceRequestListResponse(BaseModel):
    items: list[ServiceRequestResponse]


class ServiceRequestAuditResponse(BaseModel):
    action: AuditAction
    actor_id: int | None
    actor_name: str | None
    description: str
    metadata_json: str | None
    created_at: datetime


class ServiceRequestDetailResponse(ServiceRequestResponse):
    requester_name: str | None = None
    assignee_name: str | None = None
    activity: list[ServiceRequestAuditResponse] = Field(default_factory=list)


class ServiceRequestApprovalQueueResponse(BaseModel):
    items: list[ServiceRequestDetailResponse]


class ServiceRequestTransition(BaseModel):
    target_status: ServiceRequestStatus


class ServiceRequestApprovalDecision(BaseModel):
    comment: str | None = Field(None, max_length=2000)


class ServiceRequestRejectionDecision(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)



class TicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_id: int | None
    sender_type: TicketMessageSender
    content: str
    sources_json: str | None
    confidence_score: float | None
    routing_hint: str | None
    is_internal: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketConversationResponse(BaseModel):
    items: list[TicketMessageResponse]


# ─── Audit Log Schemas ────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: int
    ticket_id: int | None
    actor_id: int | None
    actor_type: str
    action: AuditAction
    description: str
    metadata_json: str | None
    confidence_score: float | None
    model_used: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Knowledge Base Schemas ──────────────────────────────────────────────────

class KBEntryCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    content: str = Field(min_length=10, max_length=50000)
    solution: str | None = Field(None, max_length=50000)
    runbook: str | None = Field(None, max_length=50000)
    category: str
    tags: str | None = None
    company_unit: str | None = None
    department: str | None = None
    applicable_to_all: bool = True


class KBEntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=200)
    content: str | None = Field(default=None, min_length=10, max_length=50000)
    solution: str | None = Field(None, max_length=50000)
    runbook: str | None = Field(None, max_length=50000)
    category: str | None = None
    tags: str | None = None
    company_unit: str | None = None
    department: str | None = None
    applicable_to_all: bool | None = None
    is_active: bool | None = None


class KBEntryResponse(BaseModel):
    id: int
    chroma_id: str | None
    title: str
    content: str
    solution: str | None
    runbook: str | None
    category: str
    tags: str | None
    company_unit: str | None
    department: str | None
    applicable_to_all: bool
    usage_count: int
    helpful_votes: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Analytics Schemas ───────────────────────────────────────────────────────

class ClassificationMetrics(BaseModel):
    total_tickets: int
    auto_classified: int
    hitl_triggered: int
    auto_closed: int
    accuracy: float | None = None
    f1_score: float | None = None
    avg_confidence: float | None = None
    low_confidence_rate: float | None = None


class SLAMetrics(BaseModel):
    total_tickets: int
    within_sla: int
    sla_breached: int
    escalated: int
    avg_resolution_hours: float | None = None
    sla_compliance_rate: float | None = None


class DashboardResponse(BaseModel):
    classification: ClassificationMetrics
    sla: SLAMetrics
    recent_tickets: list[TicketResponse]
    pending_hitl: list[TicketResponse]


# ─── Agent Process Response ──────────────────────────────────────────────────

class AgentProcessResponse(BaseModel):
    ticket_id: int
    ticket_number: str
    status: TicketStatus
    category: TicketCategory | None
    priority: TicketPriority | None
    confidence_score: float | None
    suggested_solution: str | None
    hitl_required: bool
    action_taken: str
    message: str


# ─── Token & Cost Tracking ───────────────────────────────────────────────────

class TokenUsageUserBreakdown(BaseModel):
    user_id: int | None
    username: str | None = None
    email: str | None = None
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float


class TokenUsageModelBreakdown(BaseModel):
    model_name: str
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float


class TokenUsageMetricsResponse(BaseModel):
    """Aggregated token usage and cost stats returned by GET /admin/token-usage."""

    # Overall totals
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float  # pre-rounded to 4 decimal places

    # Per-user breakdown (sorted by cost desc)
    user_breakdown: list[TokenUsageUserBreakdown]

    # Per-model breakdown (sorted by cost desc)
    model_breakdown: list[TokenUsageModelBreakdown]

