"""Pure deterministic policy resolution; callers supply DB-loaded records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.models.policy import PolicyEffect, PolicyExceptionStatus, PolicyVersionStatus, ResolvedDecision
from src.services.policy_dsl import Conditions, PolicyRule, PolicyRuleDefinition


class ResolverContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(min_length=1, max_length=64)
    company_unit: str | None = None
    department: str | None = None
    role: str | None = None
    user_id: int | None = None
    domain: str | None = None
    action_type: str | None = None
    resource: dict[str, Any] = Field(default_factory=dict)
    device: dict[str, Any] = Field(default_factory=dict)
    ticket_category: str | None = None
    risk_level: str | None = None
    request_channel: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class PolicyCitation:
    policy_id: str
    policy_key: str
    version_number: int
    title: str
    effective_from: datetime
    effect: str
    rule_id: str


@dataclass(frozen=True)
class MatchedRule:
    policy: Any
    version: Any
    rule: PolicyRule
    specificity: int
    metadata: dict[str, Any]


@dataclass
class ResolutionResult:
    resolver_revision: str
    applicable_policies: list[str] = field(default_factory=list)
    matched_rules: list[MatchedRule] = field(default_factory=list)
    matching_exceptions: list[str] = field(default_factory=list)
    decision: ResolvedDecision = ResolvedDecision.NO_DECISIVE_POLICY
    requires_approval: bool = False
    policy_citations: list[PolicyCitation] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    enforcement_error: str | None = None


def _value(context: ResolverContext, field_name: str) -> Any:
    root, *parts = field_name.split(".")
    value: Any = {
        "principal": {
            "role": context.role,
            "tenant": context.tenant_id,
            "company_unit": context.company_unit,
            "department": context.department,
            "user_id": context.user_id,
        },
        "action": {"type": context.action_type},
        "resource": context.resource,
        "device": context.device,
        "context": {
            "ticket_category": context.ticket_category,
            "risk_level": context.risk_level,
            "request_channel": context.request_channel,
        },
    }[root]
    for part in parts:
        value = value.get(part) if isinstance(value, dict) else None
    return value


def evaluate_condition(context: ResolverContext, condition: Any) -> bool:
    actual = _value(context, condition.field)
    expected = condition.value
    op = condition.operator
    if op == "exists":
        return actual is not None
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "in":
        return actual in expected
    if op == "not_in":
        return actual not in expected
    if actual is None:
        return False
    if op == "gt":
        return actual > expected
    if op == "gte":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "lte":
        return actual <= expected
    if op == "before":
        return actual < expected
    if op == "after":
        return actual > expected
    raise ValueError("unknown validated operator")


def rule_matches(context: ResolverContext, rule: PolicyRule) -> tuple[bool, dict[str, Any]]:
    if context.action_type not in rule.action:
        return False, {"reason": "action"}
    if rule.subjects.roles and context.role not in rule.subjects.roles:
        return False, {"reason": "role"}
    if rule.resource.type and context.resource.get("type") != rule.resource.type:
        return False, {"reason": "resource_type"}
    classes = rule.resource.class_
    if classes and context.resource.get("class") not in classes:
        return False, {"reason": "resource_class"}
    def evaluate_group(group: Conditions) -> bool:
        return all(
            evaluate_group(item) if isinstance(item, Conditions) else evaluate_condition(context, item)
            for item in group.all
        )

    checks = [
        evaluate_group(item) if isinstance(item, Conditions) else evaluate_condition(context, item)
        for item in rule.conditions.all
    ]
    return all(checks), {"condition_matches": checks}


def scope_matches(context: ResolverContext, scope: Any, *, policy_tenant_id: str | None) -> bool:
    if policy_tenant_id is not None and policy_tenant_id != context.tenant_id:
        return False
    if scope.tenant_id is not None and scope.tenant_id != context.tenant_id:
        return False
    fields = (
        ("company_unit", context.company_unit),
        ("department", context.department),
        ("role", context.role),
        ("user_id", context.user_id),
        ("resource_type", context.resource.get("type")),
        ("resource_class", context.resource.get("class")),
        ("policy_category", context.domain),
    )
    return all(getattr(scope, name) is None or getattr(scope, name) == actual for name, actual in fields)


def scope_specificity(scope: Any) -> int:
    weights = {
        "user_id": 100,
        "department": 30,
        "role": 25,
        "resource_type": 20,
        "resource_class": 15,
        "policy_category": 10,
        "company_unit": 5,
        "tenant_id": 1,
    }
    return sum(weight for name, weight in weights.items() if getattr(scope, name, None) is not None)


def _active(version: Any, now: datetime) -> bool:
    def as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    now = as_utc(now)
    effective_from = as_utc(version.effective_from)
    effective_until = as_utc(version.effective_until) if version.effective_until is not None else None
    return (
        version.status == PolicyVersionStatus.ACTIVE.value
        and effective_from <= now
        and (effective_until is None or effective_until > now)
    )


def applicable_policy_versions(
    context: ResolverContext,
    policies: Iterable[Any],
    versions: Iterable[Any],
    scopes: Iterable[Any],
) -> list[tuple[Any, Any]]:
    """Return current, effective policies whose scopes match this principal.

    A populated scope row is ANDed; separate matching scope rows are ORed.
    This shares the resolver's header, version, tenant, and scope semantics
    with non-enforcement consumers such as the read-only policy API.
    """
    versions_by_id = {version.id: version for version in versions}
    scopes_by_version: dict[str, list[Any]] = {}
    for scope in scopes:
        scopes_by_version.setdefault(scope.policy_version_id, []).append(scope)

    applicable: list[tuple[Any, Any]] = []
    for policy in policies:
        if policy.status != "active" or not policy.current_version_id:
            continue
        version = versions_by_id.get(policy.current_version_id)
        if version is None or not _active(version, context.timestamp):
            continue
        if any(
            scope_matches(context, scope, policy_tenant_id=policy.tenant_id)
            for scope in scopes_by_version.get(version.id, [])
        ):
            applicable.append((policy, version))
    return applicable


def _exception_matches(exc: Any, context: ResolverContext, rule: MatchedRule) -> bool:
    if exc.status != PolicyExceptionStatus.APPROVED.value or exc.tenant_id != context.tenant_id:
        return False
    def as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    if not (as_utc(exc.valid_from) <= as_utc(context.timestamp) < as_utc(exc.valid_until)):
        return False
    if exc.policy_id != rule.policy.id or (exc.policy_version_id and exc.policy_version_id != rule.version.id):
        return False
    subject_values = {
        "user": str(context.user_id),
        "department": context.department,
        "role": context.role,
    }
    if exc.subject_type not in subject_values or exc.subject_id != subject_values[exc.subject_type]:
        return False
    if exc.action_type and exc.action_type != context.action_type:
        return False
    return not exc.resource_type or exc.resource_type == context.resource.get("type")


def _revision(policies: Iterable[Any], versions: Iterable[Any], exceptions: Iterable[Any]) -> str:
    pieces = sorted(
        [f"p:{p.id}:{getattr(p, 'status', '')}:{getattr(p, 'current_version_id', '')}:{getattr(p, 'updated_at', '')}" for p in policies]
        + [
            f"v:{v.id}:{v.policy_id}:{v.status}:{v.version_number}:{v.effective_from}:{v.effective_until}:{getattr(v, 'content_hash', '')}"
            for v in versions
        ]
        + [f"e:{e.id}:{e.status}:{e.approved_at}:{e.revoked_at}" for e in exceptions]
    )
    return hashlib.sha256("|".join(pieces).encode()).hexdigest()[:24]


def resolve_policy_decision(
    context: ResolverContext,
    policies: Iterable[Any],
    versions: Iterable[Any],
    scopes: Iterable[Any],
    exceptions: Iterable[Any],
) -> ResolutionResult:
    policies = list(policies)
    versions = list(versions)
    scopes = list(scopes)
    exceptions = list(exceptions)
    result = ResolutionResult(resolver_revision=_revision(policies, versions, exceptions))
    versions_by_policy = {
        version.policy_id: version
        for version in versions
        if _active(version, context.timestamp)
    }
    scopes_by_version: dict[str, list[Any]] = {}
    for scope in scopes:
        scopes_by_version.setdefault(scope.policy_version_id, []).append(scope)
    for policy in policies:
        version = versions_by_policy.get(policy.id)
        if policy.status != "active" or version is None:
            continue
        if policy.current_version_id and version.id != policy.current_version_id:
            continue
        matching_scopes = [
            scope
            for scope in scopes_by_version.get(version.id, [])
            if scope_matches(context, scope, policy_tenant_id=policy.tenant_id)
        ]
        if not matching_scopes:
            continue
        result.applicable_policies.append(policy.id)
        try:
            definition = PolicyRuleDefinition.model_validate(json.loads(version.rule_definition_json))
        except Exception:
            result.enforcement_error = f"malformed_active_policy:{policy.id}"
            result.decision = ResolvedDecision.ESCALATE
            result.reason_codes.append("MALFORMED_ACTIVE_POLICY")
            continue
        specificity = max(scope_specificity(scope) for scope in matching_scopes)
        for rule in definition.rules:
            matched, metadata = rule_matches(context, rule)
            if matched:
                result.matched_rules.append(MatchedRule(policy, version, rule, specificity, metadata))
    allowed_exceptions: set[str] = set()
    for matched in result.matched_rules:
        if matched.rule.allow_exception and any(_exception_matches(exc, context, matched) for exc in exceptions):
            allowed_exceptions.add(matched.rule.rule_id)
            result.matching_exceptions.extend(exc.id for exc in exceptions if _exception_matches(exc, context, matched))
    effect_rank = {
        PolicyEffect.DENY: 5,
        PolicyEffect.ESCALATE: 4,
        PolicyEffect.ALLOW_WITH_APPROVAL: 3,
        PolicyEffect.ALLOW: 2,
        PolicyEffect.ADVISORY: 1,
    }
    decisive = [
        item
        for item in result.matched_rules
        if not (item.rule.effect == PolicyEffect.DENY and item.rule.rule_id in allowed_exceptions)
    ]
    decisive.sort(
        key=lambda item: (
            -effect_rank[item.rule.effect],
            -item.specificity,
            item.version.priority,
            item.policy.policy_key,
            item.rule.rule_id,
        )
    )
    if decisive:
        winner = decisive[0]
        effect = winner.rule.effect
        result.decision = {
            PolicyEffect.DENY: ResolvedDecision.DENY,
            PolicyEffect.ESCALATE: ResolvedDecision.ESCALATE,
            PolicyEffect.ALLOW_WITH_APPROVAL: ResolvedDecision.REQUIRE_APPROVAL,
            PolicyEffect.ALLOW: ResolvedDecision.ALLOW,
            PolicyEffect.ADVISORY: ResolvedDecision.NO_DECISIVE_POLICY,
        }[effect]
        result.requires_approval = effect == PolicyEffect.ALLOW_WITH_APPROVAL
        result.reason_codes.append(winner.rule.reason_code)
        result.policy_citations.append(
            PolicyCitation(
                winner.policy.id,
                winner.policy.policy_key,
                winner.version.version_number,
                winner.version.title,
                winner.version.effective_from,
                effect.value,
                winner.rule.rule_id,
            )
        )
    elif allowed_exceptions:
        result.decision = ResolvedDecision.ALLOW
        result.reason_codes.append("APPROVED_POLICY_EXCEPTION")
    return result
