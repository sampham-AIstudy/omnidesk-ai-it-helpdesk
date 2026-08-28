"""Deterministic Company Policy Engine core contracts; no runtime integration."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.models.policy import PolicyEffect, PolicyExceptionStatus, PolicyVersionStatus, ResolvedDecision
from src.services.policy_dsl import (
    MAX_CONDITION_DEPTH,
    MAX_CONDITIONS_PER_RULE,
    MAX_LIST_LENGTH,
    MAX_POLICY_CONTENT_LENGTH,
    MAX_POLICY_TITLE_LENGTH,
    MAX_RULES,
    MAX_STRING_LENGTH,
    PolicyRuleDefinition,
    normalize_policy_text,
)
from src.services.policy_resolver import ResolverContext, resolve_policy_decision, scope_matches, scope_specificity

NOW = datetime(2026, 8, 27, tzinfo=UTC)


def _rule(effect: str, action: str, *, allow_exception: bool = False, roles: list[str] | None = None) -> dict:
    return {
        "rule_id": f"r-{action}-{effect}",
        "effect": effect,
        "action": [action],
        "resource": {"type": "managed_endpoint"},
        "subjects": {"roles": roles or ["employee"]},
        "conditions": {"all": []},
        "reason_code": "POLICY_TEST",
        "user_message_template": "Restricted by policy.",
        "allow_exception": allow_exception,
    }


def _records(
    *,
    tenant: str = "automotive",
    effect: str = "deny",
    action: str = "disable_endpoint_protection",
    policy_key: str = "POL-ENDPOINT-001",
    allow_exception: bool = False,
    priority: int = 100,
):
    policy = SimpleNamespace(
        id="p1", policy_key=policy_key, tenant_id=tenant, status="active", current_version_id="v1", updated_at=NOW
    )
    version = SimpleNamespace(
        id="v1",
        policy_id="p1",
        version_number=1,
        title="Endpoint",
        effective_from=NOW - timedelta(days=1),
        effective_until=None,
        status=PolicyVersionStatus.ACTIVE.value,
        priority=priority,
        rule_definition_json=json.dumps(
            {
                "schema_version": 1,
                "default_effect": "advisory",
                "rules": [_rule(effect, action, allow_exception=allow_exception)],
            }
        ),
    )
    scope = SimpleNamespace(
        policy_version_id="v1",
        tenant_id=tenant,
        company_unit=None,
        department=None,
        role=None,
        user_id=None,
        resource_type="managed_endpoint",
        resource_class=None,
        policy_category=None,
    )
    return policy, version, scope


def _context(**updates) -> ResolverContext:
    base = {
        "tenant_id": "automotive",
        "company_unit": "automotive",
        "department": "IT",
        "role": "employee",
        "user_id": 7,
        "domain": "endpoint_security",
        "action_type": "disable_endpoint_protection",
        "resource": {"type": "managed_endpoint", "class": "windows_endpoint", "managed": True},
        "timestamp": NOW,
    }
    base.update(updates)
    return ResolverContext(**base)


def test_rule_dsl_rejects_unknowns_duplicate_ids_and_oversize_content():
    valid = {"schema_version": 1, "rules": [_rule("deny", "disable_endpoint_protection")]}
    assert PolicyRuleDefinition.model_validate(valid).rules[0].effect is PolicyEffect.DENY
    bad = _rule("deny", "disable_endpoint_protection")
    bad["conditions"] = {"all": [{"field": "system.shell", "operator": "eq", "value": "x"}]}
    with pytest.raises(ValidationError):
        PolicyRuleDefinition.model_validate({"schema_version": 1, "rules": [bad]})
    with pytest.raises(ValidationError):
        PolicyRuleDefinition.model_validate({"schema_version": 1, "rules": [valid["rules"][0], valid["rules"][0]]})
    with pytest.raises(ValueError):
        normalize_policy_text("x" * (MAX_POLICY_CONTENT_LENGTH + 1), maximum=MAX_POLICY_CONTENT_LENGTH)


def test_scope_and_tenant_isolation_and_global_baseline():
    scope = SimpleNamespace(
        tenant_id="automotive",
        company_unit=None,
        department="IT",
        role="employee",
        user_id=7,
        resource_type="managed_endpoint",
        resource_class=None,
        policy_category="endpoint_security",
    )
    assert scope_matches(_context(), scope, policy_tenant_id="automotive")
    assert not scope_matches(_context(tenant_id="healthcare"), scope, policy_tenant_id="automotive")
    assert scope_specificity(scope) > 100
    global_scope = SimpleNamespace(
        tenant_id=None,
        company_unit=None,
        department=None,
        role=None,
        user_id=None,
        resource_type="managed_endpoint",
        resource_class=None,
        policy_category=None,
    )
    assert scope_matches(_context(tenant_id="healthcare"), global_scope, policy_tenant_id=None)


def test_deny_wins_over_more_specific_allow_without_exception():
    deny_policy, deny_version, deny_scope = _records(effect="deny")
    allow_policy, allow_version, allow_scope = _records(effect="allow", policy_key="POL-USER-ALLOW")
    allow_policy.id, allow_version.id, allow_version.policy_id, allow_scope.policy_version_id = "p2", "v2", "p2", "v2"
    allow_scope.user_id = 7
    result = resolve_policy_decision(
        _context(), [deny_policy, allow_policy], [deny_version, allow_version], [deny_scope, allow_scope], []
    )
    assert result.decision is ResolvedDecision.DENY


def test_approved_time_bounded_exception_can_bypass_explicit_denial_only():
    policy, version, scope = _records(allow_exception=True)
    exc = SimpleNamespace(
        id="e1",
        status=PolicyExceptionStatus.APPROVED.value,
        tenant_id="automotive",
        valid_from=NOW - timedelta(minutes=1),
        valid_until=NOW + timedelta(minutes=1),
        policy_id="p1",
        policy_version_id="v1",
        subject_type="user",
        subject_id="7",
        action_type="disable_endpoint_protection",
        resource_type="managed_endpoint",
        approved_at=NOW,
        revoked_at=None,
    )
    result = resolve_policy_decision(_context(), [policy], [version], [scope], [exc])
    assert result.decision is ResolvedDecision.ALLOW
    assert result.matching_exceptions == ["e1"]
    policy2, version2, scope2 = _records(allow_exception=False)
    result = resolve_policy_decision(_context(), [policy2], [version2], [scope2], [exc])
    assert result.decision is ResolvedDecision.DENY


def test_effect_order_and_fail_closed_malformed_active_policy():
    allow_policy, allow_version, allow_scope = _records(effect="allow")
    esc_policy, esc_version, esc_scope = _records(effect="escalate", policy_key="POL-ESC")
    esc_policy.id, esc_version.id, esc_version.policy_id, esc_scope.policy_version_id = "p2", "v2", "p2", "v2"
    esc_policy.current_version_id = "v2"
    assert (
        resolve_policy_decision(
            _context(), [allow_policy, esc_policy], [allow_version, esc_version], [allow_scope, esc_scope], []
        ).decision
        is ResolvedDecision.ESCALATE
    )
    allow_version.rule_definition_json = "{bad"
    result = resolve_policy_decision(_context(), [allow_policy], [allow_version], [allow_scope], [])
    assert result.decision is ResolvedDecision.ESCALATE
    assert result.enforcement_error


def test_future_superseded_and_wrong_tenant_versions_do_not_apply():
    policy, version, scope = _records()
    version.effective_from = NOW + timedelta(days=1)
    assert (
        resolve_policy_decision(_context(), [policy], [version], [scope], []).decision
        is ResolvedDecision.NO_DECISIVE_POLICY
    )


def _nested_conditions(depth: int) -> dict:
    node: dict = {"field": "action.type", "operator": "eq", "value": "disable_endpoint_protection"}
    for _ in range(depth - 1):
        node = {"all": [node]}
    return {"all": [node]}


def _rules(count: int) -> list[dict]:
    return [{**_rule("deny", "disable_endpoint_protection"), "rule_id": f"rule-{index}"} for index in range(count)]


@pytest.mark.parametrize(
    ("label", "payload", "valid"),
    [
        ("rules_below", {"rules": _rules(MAX_RULES - 1)}, True),
        ("rules_at", {"rules": _rules(MAX_RULES)}, True),
        ("rules_above", {"rules": _rules(MAX_RULES + 1)}, False),
        ("conditions_below", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "conditions": {"all": [{"field": "action.type", "operator": "eq", "value": "disable_endpoint_protection"}] * (MAX_CONDITIONS_PER_RULE - 1)}}]}, True),
        ("conditions_at", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "conditions": {"all": [{"field": "action.type", "operator": "eq", "value": "disable_endpoint_protection"}] * MAX_CONDITIONS_PER_RULE}}]}, True),
        ("conditions_above", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "conditions": {"all": [{"field": "action.type", "operator": "eq", "value": "disable_endpoint_protection"}] * (MAX_CONDITIONS_PER_RULE + 1)}}]}, False),
        ("depth_below", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "conditions": _nested_conditions(MAX_CONDITION_DEPTH - 1)}]}, True),
        ("depth_at", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "conditions": _nested_conditions(MAX_CONDITION_DEPTH)}]}, True),
        ("depth_above", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "conditions": _nested_conditions(MAX_CONDITION_DEPTH + 1)}]}, False),
        ("list_below", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "action": ["x"] * (MAX_LIST_LENGTH - 1)}]}, True),
        ("list_at", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "action": ["x"] * MAX_LIST_LENGTH}]}, True),
        ("list_above", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "action": ["x"] * (MAX_LIST_LENGTH + 1)}]}, False),
        ("string_below", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "user_message_template": "x" * (MAX_STRING_LENGTH - 1)}]}, True),
        ("string_at", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "user_message_template": "x" * MAX_STRING_LENGTH}]}, True),
        ("string_above", {"rules": [{**_rule("deny", "disable_endpoint_protection"), "user_message_template": "x" * (MAX_STRING_LENGTH + 1)}]}, False),
    ],
)
def test_dsl_limit_boundary_matrix(label, payload, valid):
    payload = {"schema_version": 1, **payload}
    if valid:
        PolicyRuleDefinition.model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            PolicyRuleDefinition.model_validate(payload)


@pytest.mark.parametrize("limit", [MAX_POLICY_TITLE_LENGTH, MAX_POLICY_CONTENT_LENGTH])
def test_policy_text_limit_boundaries(limit):
    assert normalize_policy_text("x" * (limit - 1), maximum=limit)
    assert normalize_policy_text("x" * limit, maximum=limit)
    with pytest.raises(ValueError):
        normalize_policy_text("x" * (limit + 1), maximum=limit)


def test_dsl_rejects_unknown_operator_effect_and_schema_version():
    for key, value in (("operator", "unknown"), ("effect", "unknown")):
        rule = _rule("deny", "disable_endpoint_protection")
        if key == "operator":
            rule["conditions"] = {"all": [{"field": "action.type", key: value, "value": "x"}]}
        else:
            rule[key] = value
        with pytest.raises(ValidationError):
            PolicyRuleDefinition.model_validate({"schema_version": 1, "rules": [rule]})
    with pytest.raises(ValidationError):
        PolicyRuleDefinition.model_validate({"schema_version": 2, "rules": []})


def test_explicit_tenant_global_and_missing_tenant_matrix():
    automotive, av, a_scope = _records(tenant="automotive")
    healthcare, hv, h_scope = _records(tenant="healthcare", policy_key="HEALTH")
    healthcare.id, hv.id, hv.policy_id, h_scope.policy_version_id = "p2", "v2", "p2", "v2"
    healthcare.current_version_id = "v2"
    global_policy, gv, global_scope = _records(tenant=None, policy_key="GLOBAL")
    global_policy.id, gv.id, gv.policy_id, global_scope.policy_version_id, global_scope.tenant_id = "p3", "v3", "p3", "v3", None
    global_policy.current_version_id = "v3"
    assert resolve_policy_decision(_context(tenant_id="automotive"), [automotive], [av], [a_scope], []).decision is ResolvedDecision.DENY
    assert resolve_policy_decision(_context(tenant_id="healthcare"), [automotive], [av], [a_scope], []).decision is ResolvedDecision.NO_DECISIVE_POLICY
    assert resolve_policy_decision(_context(tenant_id="healthcare"), [healthcare], [hv], [h_scope], []).decision is ResolvedDecision.DENY
    assert resolve_policy_decision(_context(tenant_id="automotive"), [healthcare], [hv], [h_scope], []).decision is ResolvedDecision.NO_DECISIVE_POLICY
    assert resolve_policy_decision(_context(tenant_id="automotive"), [global_policy], [gv], [global_scope], []).decision is ResolvedDecision.DENY
    assert resolve_policy_decision(_context(tenant_id="healthcare"), [global_policy], [gv], [global_scope], []).decision is ResolvedDecision.DENY


@pytest.mark.parametrize("attribute, value", [
    ("status", PolicyExceptionStatus.PENDING.value), ("status", PolicyExceptionStatus.REJECTED.value),
    ("status", PolicyExceptionStatus.EXPIRED.value), ("status", PolicyExceptionStatus.REVOKED.value),
    ("tenant_id", "healthcare"), ("subject_id", "999"), ("action_type", "other"), ("resource_type", "other"),
])
def test_exception_mismatch_matrix_keeps_hard_deny(attribute, value):
    policy, version, scope = _records(allow_exception=True)
    exc = SimpleNamespace(id="e1", status=PolicyExceptionStatus.APPROVED.value, tenant_id="automotive", valid_from=NOW - timedelta(minutes=1), valid_until=NOW + timedelta(minutes=1), policy_id="p1", policy_version_id="v1", subject_type="user", subject_id="7", action_type="disable_endpoint_protection", resource_type="managed_endpoint", approved_at=NOW, revoked_at=None)
    setattr(exc, attribute, value)
    assert resolve_policy_decision(_context(), [policy], [version], [scope], [exc]).decision is ResolvedDecision.DENY


def test_resolver_revision_tracks_enforcement_state_changes():
    policy, version, scope = _records()
    unchanged = resolve_policy_decision(_context(), [policy], [version], [scope], []).resolver_revision
    assert unchanged == resolve_policy_decision(_context(), [policy], [version], [scope], []).resolver_revision
    version.status = PolicyVersionStatus.DRAFT.value
    draft = resolve_policy_decision(_context(), [policy], [version], [scope], []).resolver_revision
    version.status = PolicyVersionStatus.ACTIVE.value
    activated = resolve_policy_decision(_context(), [policy], [version], [scope], []).resolver_revision
    assert draft != activated
    policy.status = "inactive"
    assert activated != resolve_policy_decision(_context(), [policy], [version], [scope], []).resolver_revision
    policy.status, version.status = "active", PolicyVersionStatus.SUPERSEDED.value
    version2 = SimpleNamespace(**{**version.__dict__, "id": "v2", "version_number": 2, "status": "active"})
    policy.current_version_id = "v2"
    assert activated != resolve_policy_decision(_context(), [policy], [version, version2], [scope], []).resolver_revision
    exc = SimpleNamespace(id="e1", status=PolicyExceptionStatus.APPROVED.value, approved_at=NOW, revoked_at=None)
    approved = resolve_policy_decision(_context(), [policy], [version, version2], [scope], [exc]).resolver_revision
    exc.status, exc.revoked_at = PolicyExceptionStatus.REVOKED.value, NOW
    assert approved != resolve_policy_decision(_context(), [policy], [version, version2], [scope], [exc]).resolver_revision


@pytest.mark.parametrize("definition", [
    "{bad",
    json.dumps({"schema_version": 2, "rules": []}),
    json.dumps({"schema_version": 1, "rules": [{**_rule("deny", "disable_endpoint_protection"), "effect": "unknown"}]}),
    json.dumps({"schema_version": 1, "rules": [{"rule_id": "bad", "effect": "deny"}]}),
])
def test_active_unknown_or_malformed_dsl_fails_closed(definition):
    policy, version, scope = _records()
    version.rule_definition_json = definition
    result = resolve_policy_decision(_context(), [policy], [version], [scope], [])
    assert result.decision is ResolvedDecision.ESCALATE
    assert result.enforcement_error
    version.effective_from = NOW - timedelta(days=1)
    version.status = PolicyVersionStatus.SUPERSEDED.value
    assert (
        resolve_policy_decision(_context(), [policy], [version], [scope], []).decision
        is ResolvedDecision.NO_DECISIVE_POLICY
    )
