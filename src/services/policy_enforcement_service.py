"""Single canonical policy enforcement service for runtime workflows."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.policy import (
    Policy,
    PolicyAuditEvent,
    PolicyException,
    PolicyExceptionStatus,
    PolicyScope,
    PolicyVersion,
    PolicyVersionStatus,
    ResolvedDecision,
)
from src.services.policy_resolver import (
    MatchedRule,
    PolicyCitation,
    ResolutionResult,
    ResolverContext,
    resolve_policy_decision,
)

logger = logging.getLogger(__name__)

# Cache structure: tenant_id -> (cache_timestamp, revision_hash, policies, versions, scopes, exceptions)
_POLICY_CACHE_TTL_SECONDS = 60.0
_policy_cache: dict[str, tuple[float, str, list[Policy], list[PolicyVersion], list[PolicyScope], list[PolicyException]]] = {}


def clear_policy_cache(tenant_id: str | None = None) -> None:
    """Invalidate cached policy definitions globally or for a specific tenant."""
    if tenant_id:
        _policy_cache.pop(tenant_id, None)
    else:
        _policy_cache.clear()


@dataclass
class EnforcementResult:
    decision: ResolvedDecision
    allowed: bool
    requires_approval: bool
    escalate: bool
    reason: str
    reason_codes: list[str] = field(default_factory=list)
    policy_citations: list[PolicyCitation] = field(default_factory=list)
    matched_rules: list[MatchedRule] = field(default_factory=list)
    matching_exceptions: list[str] = field(default_factory=list)
    enforcement_error: str | None = None


async def _load_tenant_policy_records(
    db: AsyncSession, tenant_id: str
) -> tuple[list[Policy], list[PolicyVersion], list[PolicyScope], list[PolicyException]]:
    """Load active policies, versions, scopes, and exceptions for a tenant from database."""
    import time
    now_ts = time.time()
    if _POLICY_CACHE_TTL_SECONDS > 0:
        try:
            cached = _policy_cache.get(tenant_id)
            if cached and (now_ts - cached[0] < _POLICY_CACHE_TTL_SECONDS):
                return cached[2], cached[3], cached[4], cached[5]
        except Exception as exc:
            logger.warning("Policy cache read failed for tenant %s; using database: %s", tenant_id, exc)

    now_dt = datetime.now(UTC)

    # 1. Policies: Active global (tenant_id IS NULL) or tenant-specific
    p_stmt = select(Policy).where(
        Policy.status == "active",
        or_(Policy.tenant_id.is_(None), Policy.tenant_id == tenant_id),
    )
    p_res = await db.execute(p_stmt)
    policies = list(p_res.scalars().all())
    policy_ids = [p.id for p in policies]

    if not policy_ids:
        if _POLICY_CACHE_TTL_SECONDS > 0:
            try:
                _policy_cache[tenant_id] = (now_ts, "empty", [], [], [], [])
            except Exception as exc:
                logger.warning("Policy cache write failed for tenant %s: %s", tenant_id, exc)
        return [], [], [], []

    # 2. Versions: Active versions of matching policies within effective window
    v_stmt = select(PolicyVersion).where(
        PolicyVersion.policy_id.in_(policy_ids),
        PolicyVersion.status == PolicyVersionStatus.ACTIVE.value,
        PolicyVersion.effective_from <= now_dt,
        or_(PolicyVersion.effective_until.is_(None), PolicyVersion.effective_until > now_dt),
    )
    v_res = await db.execute(v_stmt)
    versions = list(v_res.scalars().all())
    version_ids = [v.id for v in versions]

    # 3. Scopes: Scopes attached to active versions for tenant or global
    scopes: list[PolicyScope] = []
    if version_ids:
        s_stmt = select(PolicyScope).where(
            PolicyScope.policy_version_id.in_(version_ids),
            or_(PolicyScope.tenant_id.is_(None), PolicyScope.tenant_id == tenant_id),
        )
        s_res = await db.execute(s_stmt)
        scopes = list(s_res.scalars().all())

    # 4. Exceptions: Approved exceptions valid at current time for this tenant
    e_stmt = select(PolicyException).where(
        PolicyException.policy_id.in_(policy_ids),
        PolicyException.tenant_id == tenant_id,
        PolicyException.status == PolicyExceptionStatus.APPROVED.value,
        PolicyException.valid_from <= now_dt,
        PolicyException.valid_until > now_dt,
    )
    e_res = await db.execute(e_stmt)
    exceptions = list(e_res.scalars().all())

    if _POLICY_CACHE_TTL_SECONDS > 0:
        try:
            _policy_cache[tenant_id] = (now_ts, "loaded", policies, versions, scopes, exceptions)
        except Exception as exc:
            logger.warning("Policy cache write failed for tenant %s: %s", tenant_id, exc)
    return policies, versions, scopes, exceptions


async def enforce_policy(
    db: AsyncSession | None,
    *,
    tenant_id: str,
    action_type: str,
    actor_id: int | None = None,
    role: str | None = None,
    company_unit: str | None = None,
    department: str | None = None,
    resource: dict[str, Any] | None = None,
    ticket_id: int | None = None,
    ticket_category: str | None = None,
    risk_level: str | None = None,
    request_channel: str | None = None,
    trace_id: str | None = None,
    policies: list[Policy] | None = None,
    versions: list[PolicyVersion] | None = None,
    scopes: list[PolicyScope] | None = None,
    exceptions: list[PolicyException] | None = None,
    record_audit: bool = True,
) -> EnforcementResult:
    """Canonical entry point to evaluate company policy for any runtime action."""
    if not tenant_id:
        return EnforcementResult(
            decision=ResolvedDecision.ESCALATE,
            allowed=False,
            requires_approval=False,
            escalate=True,
            reason="Missing trusted tenant_id for policy evaluation (fail-closed).",
            reason_codes=["MISSING_TENANT_ID"],
            enforcement_error="missing_tenant_id",
        )

    context = ResolverContext(
        tenant_id=tenant_id,
        company_unit=company_unit or tenant_id,
        department=department,
        role=role,
        user_id=actor_id,
        action_type=action_type,
        resource=resource or {},
        ticket_category=ticket_category,
        risk_level=risk_level,
        request_channel=request_channel,
        timestamp=datetime.now(UTC),
    )

    try:
        if policies is None or versions is None or scopes is None or exceptions is None:
            if db is None:
                raise ValueError("AsyncSession is required when policy records are not pre-supplied.")
            policies, versions, scopes, exceptions = await _load_tenant_policy_records(db, tenant_id)

        resolution: ResolutionResult = resolve_policy_decision(
            context,
            policies=policies,
            versions=versions,
            scopes=scopes,
            exceptions=exceptions,
        )
    except Exception as exc:
        logger.error("Policy evaluation error for tenant %s action %s: %s", tenant_id, action_type, exc)
        return EnforcementResult(
            decision=ResolvedDecision.ESCALATE,
            allowed=False,
            requires_approval=False,
            escalate=True,
            reason=f"Policy evaluation failed safely (fail-closed): {exc}",
            reason_codes=["RESOLVER_ERROR"],
            enforcement_error=str(exc),
        )

    decision = resolution.decision
    allowed = decision in (ResolvedDecision.ALLOW, ResolvedDecision.NO_DECISIVE_POLICY)
    requires_approval = decision == ResolvedDecision.REQUIRE_APPROVAL
    escalate = decision == ResolvedDecision.ESCALATE

    winner_citation = resolution.policy_citations[0] if resolution.policy_citations else None
    reason = (
        f"Policy {winner_citation.policy_key} ({winner_citation.rule_id}): {winner_citation.effect.upper()}"
        if winner_citation
        else "No decisive company policy applied."
    )

    result = EnforcementResult(
        decision=decision,
        allowed=allowed,
        requires_approval=requires_approval,
        escalate=escalate,
        reason=reason,
        reason_codes=resolution.reason_codes,
        policy_citations=resolution.policy_citations,
        matched_rules=resolution.matched_rules,
        matching_exceptions=resolution.matching_exceptions,
        enforcement_error=resolution.enforcement_error,
    )

    # Audit logging for decisive decisions or security-relevant denials/escalations
    if record_audit and db is not None and decision != ResolvedDecision.NO_DECISIVE_POLICY:
        try:
            audit_event = PolicyAuditEvent(
                tenant_id=tenant_id,
                actor_id=actor_id,
                principal_id=actor_id,
                policy_id=winner_citation.policy_id if winner_citation else None,
                policy_version_id=resolution.matched_rules[0].version.id if resolution.matched_rules else None,
                policy_exception_id=resolution.matching_exceptions[0] if resolution.matching_exceptions else None,
                ticket_id=ticket_id,
                trace_id=trace_id,
                event_type=f"policy_enforcement:{action_type}",
                decision=decision.value,
                rule_id=winner_citation.rule_id if winner_citation else None,
                reason_code=resolution.reason_codes[0] if resolution.reason_codes else None,
                metadata_json=json.dumps({
                    "action_type": action_type,
                    "resource": resource or {},
                    "reason": reason,
                    "matched_count": len(resolution.matched_rules),
                }, ensure_ascii=False),
            )
            db.add(audit_event)
            await db.flush()
        except Exception as exc:
            logger.warning("Could not write PolicyAuditEvent for ticket %s: %s", ticket_id, exc)

    return result
