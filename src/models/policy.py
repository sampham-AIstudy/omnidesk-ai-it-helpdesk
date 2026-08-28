"""Immutable, tenant-scoped Company Policy Engine domain records."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, event, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class PolicyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PolicyVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    REJECTED = "rejected"


class PolicyExceptionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REVOKED = "revoked"
    EXPIRED = "expired"
    REJECTED = "rejected"


class PolicyEffect(str, enum.Enum):
    DENY = "deny"
    ALLOW = "allow"
    ALLOW_WITH_APPROVAL = "allow_with_approval"
    ESCALATE = "escalate"
    ADVISORY = "advisory"


class ResolvedDecision(str, enum.Enum):
    DENY = "deny"
    ESCALATE = "escalate"
    REQUIRE_APPROVAL = "require_approval"
    ALLOW = "allow"
    NO_DECISIVE_POLICY = "no_decisive_policy"


class OutputEnforcementDecision(str, enum.Enum):
    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"
    ESCALATE = "escalate"


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "policy_key", name="uq_policies_tenant_key"),
        CheckConstraint("status IN ('draft','active','inactive','archived')", name="ck_policies_status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    policy_key: Mapped[str] = mapped_column(String(80), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PolicyStatus.DRAFT.value, index=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    deactivated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("policy_id", "version_number", name="uq_policy_versions_number"),
        CheckConstraint("priority >= 0 AND priority <= 10000", name="ck_policy_versions_priority"),
        CheckConstraint("effective_until IS NULL OR effective_until > effective_from", name="ck_policy_versions_window"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rule_definition_json: Mapped[str] = mapped_column(Text, nullable=False)
    effect_summary: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PolicyVersionStatus.DRAFT.value, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    activated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    supersedes_version_id: Mapped[str | None] = mapped_column(ForeignKey("policy_versions.id"), nullable=True)


class PolicyScope(Base):
    __tablename__ = "policy_scopes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("policy_versions.id"), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    company_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    policy_category: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PolicyException(Base):
    __tablename__ = "policy_exceptions"
    __table_args__ = (CheckConstraint("valid_until > valid_from", name="ck_policy_exceptions_window"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False, index=True)
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("policy_versions.id"), nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    action_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_selector_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_effect: Mapped[str] = mapped_column(String(32), nullable=False, default=PolicyEffect.ALLOW.value)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PolicyExceptionStatus.PENDING.value, index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    revoked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PolicyAuditEvent(Base):
    __tablename__ = "policy_audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    principal_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("policies.id"), nullable=True, index=True)
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("policy_versions.id"), nullable=True)
    policy_exception_id: Mapped[str | None] = mapped_column(ForeignKey("policy_exceptions.id"), nullable=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    before_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


@event.listens_for(PolicyVersion, "before_update")
def _protect_policy_version(_mapper, _connection, target: PolicyVersion) -> None:
    from sqlalchemy import inspect
    state = inspect(target)
    original = state.attrs.status.history.deleted
    prior_status = original[0] if original else target.status
    immutable = {PolicyVersionStatus.APPROVED.value, PolicyVersionStatus.ACTIVE.value}
    protected = {"title", "content", "rule_definition_json", "effect_summary", "priority", "effective_from", "effective_until", "content_hash", "policy_id", "version_number"}
    if prior_status in immutable and any(state.attrs[name].history.has_changes() for name in protected):
        raise ValueError("Approved and active PolicyVersion content is immutable")


@event.listens_for(PolicyAuditEvent, "before_update")
def _reject_policy_audit_update(*_args) -> None:
    raise ValueError("PolicyAuditEvent rows are immutable")


@event.listens_for(PolicyAuditEvent, "before_delete")
def _reject_policy_audit_delete(*_args) -> None:
    raise ValueError("PolicyAuditEvent rows are append-only")
