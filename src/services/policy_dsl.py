"""Constrained, deterministic policy-rule DSL. Never executes author text."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.models.policy import PolicyEffect

MAX_RULES = 50
MAX_CONDITIONS_PER_RULE = 20
MAX_CONDITION_DEPTH = 4
MAX_LIST_LENGTH = 50
MAX_STRING_LENGTH = 500
MAX_POLICY_TITLE_LENGTH = 255
MAX_POLICY_CONTENT_LENGTH = 50_000
ALLOWED_FIELDS = frozenset({"principal.role", "principal.tenant", "principal.company_unit", "principal.department", "principal.user_id", "action.type", "resource.type", "resource.class", "resource.managed", "resource.service_name", "resource.software_id", "context.ticket_category", "context.risk_level", "context.request_channel", "device.managed", "device.os", "device.ownership_class"})
ALLOWED_OPERATORS = frozenset({"eq", "neq", "in", "not_in", "exists", "gt", "gte", "lt", "lte", "before", "after"})
_UNSAFE_DIRECTIVE = re.compile(r"(?i)(ignore\s+(?:all\s+)?(?:previous|system)\s+instructions|reveal\s+(?:system|developer)\s+prompt|\b(?:eval|exec|import)\s*\()")


def normalize_policy_text(value: str, *, maximum: int) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = "".join(char for char in normalized if char >= " " or char in "\n\t")
    normalized = re.sub(r"<[^>]{1,200}>", "", normalized).strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"policy text must be between 1 and {maximum} characters")
    if _UNSAFE_DIRECTIVE.search(normalized):
        raise ValueError("policy text contains prohibited directive-shaped content")
    return normalized


def policy_content_hash(*, title: str, content: str, rule_definition: dict[str, Any]) -> str:
    payload = json.dumps({"title": title, "content": content, "rules": rule_definition}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    operator: str
    value: Any = None

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str) -> str:
        if value not in ALLOWED_FIELDS:
            raise ValueError("unknown policy condition field")
        return value

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        if value not in ALLOWED_OPERATORS:
            raise ValueError("unknown policy condition operator")
        return value

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Any) -> Any:
        if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
            raise ValueError("condition string exceeds limit")
        if isinstance(value, list) and len(value) > MAX_LIST_LENGTH:
            raise ValueError("condition list exceeds limit")
        return value


class Conditions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    all: list[Condition | Conditions] = Field(default_factory=list)

    @field_validator("all")
    @classmethod
    def validate_count(cls, value: list[Condition | Conditions]) -> list[Condition | Conditions]:
        if len(value) > MAX_CONDITIONS_PER_RULE:
            raise ValueError("too many conditions")
        return value

    @model_validator(mode="after")
    def validate_depth(self) -> Conditions:
        def depth(group: Conditions) -> int:
            return 1 + max((depth(item) for item in group.all if isinstance(item, Conditions)), default=0)

        if depth(self) > MAX_CONDITION_DEPTH:
            raise ValueError("condition nesting exceeds limit")
        return self


class RuleResource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str | None = Field(default=None, max_length=MAX_STRING_LENGTH)
    class_: list[str] = Field(default_factory=list, alias="class", max_length=MAX_LIST_LENGTH)


class RuleSubjects(BaseModel):
    model_config = ConfigDict(extra="forbid")
    roles: list[str] = Field(default_factory=list, max_length=MAX_LIST_LENGTH)


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    rule_id: str = Field(min_length=1, max_length=128)
    effect: PolicyEffect
    action: list[str] = Field(min_length=1, max_length=MAX_LIST_LENGTH)
    resource: RuleResource = Field(default_factory=RuleResource)
    subjects: RuleSubjects = Field(default_factory=RuleSubjects)
    conditions: Conditions = Field(default_factory=Conditions)
    reason_code: str = Field(min_length=1, max_length=128)
    user_message_template: str = Field(min_length=1, max_length=MAX_STRING_LENGTH)
    allow_exception: bool = False


class PolicyRuleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = Field(ge=1, le=1)
    default_effect: PolicyEffect = PolicyEffect.ADVISORY
    rules: list[PolicyRule] = Field(default_factory=list, max_length=MAX_RULES)

    @model_validator(mode="after")
    def unique_rule_ids(self) -> PolicyRuleDefinition:
        if len({rule.rule_id for rule in self.rules}) != len(self.rules):
            raise ValueError("rule_id values must be unique")
        return self
