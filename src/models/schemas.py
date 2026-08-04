"""Pydantic schemas — Request/Response models cho API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from src.models.audit_log import AuditAction
from src.models.ticket import TicketCategory, TicketPriority, TicketStatus, TicketUrgency
from src.models.user import CompanyUnit, UserRole


# ─── Auth Schemas ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    company_unit: CompanyUnit
    department: str | None
    is_vip: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6)
    role: UserRole = UserRole.EMPLOYEE
    company_unit: CompanyUnit = CompanyUnit.CORPORATE
    department: str | None = None
    is_vip: bool = False


# ─── Ticket Schemas ──────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: str = Field(min_length=10)
    is_production_impact: bool = False


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    category: TicketCategory | None
    priority: TicketPriority | None
    urgency: TicketUrgency | None
    confidence_score: float | None
    suggested_solution: str | None
    rag_sources: str | None
    agent_reasoning: str | None
    routing_target: str | None
    is_production_impact: bool
    status: TicketStatus
    hitl_required: bool
    hitl_note: str | None
    hitl_decided_at: datetime | None
    submitter_id: int
    assignee_id: int | None
    sla_deadline: datetime | None
    sla_warning_sent: bool
    sla_escalated: bool
    first_response_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    page: int
    page_size: int


class HITLDecisionRequest(BaseModel):
    approved: bool
    note: str | None = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    note: str | None = None


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
    title: str = Field(min_length=5, max_length=255)
    content: str = Field(min_length=10)
    solution: str | None = None
    runbook: str | None = None
    category: str
    tags: str | None = None
    company_unit: str | None = None
    department: str | None = None
    applicable_to_all: bool = True


class KBEntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=255)
    content: str | None = Field(default=None, min_length=10)
    solution: str | None = None
    runbook: str | None = None
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
