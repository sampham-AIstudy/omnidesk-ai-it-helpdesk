"""Small, trusted policy envelope for non-KB generator responses.

This is deliberately not a response planner. It has no request parsing,
evidence/support classification, coverage mode, or intent inference. Every
field is copied from an already-authoritative runtime component.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from src.services.action_grounding import ActionResult, may_confirm_action
from src.services.chat_routing_service import ChatRouteDecision
from src.services.incident_fact_profiles import IncidentFactState

SecurityDecision = Literal["ALLOW", "BLOCK"]
AuthorizationState = Literal["TRUSTED_SESSION", "DENIED", "NOT_APPLICABLE"]


@dataclass(frozen=True)
class GeneratorPolicy:
    """Authoritative state constraints; it never makes a routing decision."""

    route: str
    security_decision: SecurityDecision
    authorization_state: AuthorizationState
    tool_invoked: bool
    tool_success: bool | None
    tool_result_summary: str | None
    trusted_known_facts: dict[str, str]
    missing_required_facts: tuple[str, ...]
    allow_knowledge_claims: bool
    allow_action_success_claim: bool
    clarification_allowed: bool
    response_constraints: tuple[str, ...]
    field_sources: dict[str, str]

    @property
    def eligible_non_kb_route(self) -> bool:
        return self.security_decision == "BLOCK" or self.route in {
            "direct_response",
            "needs_clarification",
            "ticket_status",
            "action_request",
        }

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def as_prompt_block(self) -> str:
        """Short envelope for a rare non-deterministic caller."""
        constraints = "; ".join(self.response_constraints)
        facts = self.trusted_known_facts or {"none": "none"}
        return (
            "[TRUSTED_RUNTIME_STATE]\n"
            f"route={self.route}; security={self.security_decision}; authorization={self.authorization_state}; "
            f"tool_invoked={self.tool_invoked}; tool_success={self.tool_success}; facts={facts}\n"
            "Do not reinterpret route, security, authorization, or tool state. "
            f"Constraints: {constraints}"
        )


def build_generator_policy(
    *,
    route_decision: ChatRouteDecision,
    security_decision: SecurityDecision,
    authorization_state: AuthorizationState,
    action_result: ActionResult | None = None,
    incident_facts: IncidentFactState | None = None,
) -> GeneratorPolicy:
    """Copy trusted state into a small contract without deriving new state."""
    facts = dict(incident_facts.known_facts) if incident_facts else {}
    missing = tuple(incident_facts.missing_required_facts) if incident_facts else ()
    tool_invoked = action_result is not None
    tool_success = action_result.success if action_result is not None else None
    action_confirmed = may_confirm_action(action_result) if action_result is not None else False

    constraints = ["Do not reinterpret trusted route, security, authorization, or tool state."]
    if security_decision == "BLOCK":
        constraints.extend(("Do not use KB, memory, web, or tools.", "Give only the approved safe response."))
    elif route_decision.route == "direct_response":
        constraints.extend(("Remain a direct response.", "Do not add IT policy, ticket, or diagnosis claims."))
    elif route_decision.route == "needs_clarification":
        constraints.append("Ask only facts already listed as missing required facts.")
    elif route_decision.route in {"ticket_status", "action_request"}:
        constraints.append("Never claim an action completed without a successful trusted tool result.")

    return GeneratorPolicy(
        route=route_decision.route,
        security_decision=security_decision,
        authorization_state=authorization_state,
        tool_invoked=tool_invoked,
        tool_success=tool_success,
        tool_result_summary=(
            f"resource_id={action_result.resource_id}; persisted_state={action_result.persisted_state}"
            if action_result is not None
            else None
        ),
        trusted_known_facts=facts,
        missing_required_facts=missing,
        allow_knowledge_claims=security_decision == "ALLOW" and route_decision.should_retrieve,
        allow_action_success_claim=security_decision == "ALLOW" and action_confirmed,
        clarification_allowed=(
            security_decision == "ALLOW"
            and route_decision.route == "needs_clarification"
            and bool(missing)
        ),
        response_constraints=tuple(constraints),
        field_sources={
            "route": "chat_routing_service",
            "security_decision": "input_guardrails",
            "authorization_state": "authenticated_request_context",
            "tool_invoked": "action_result",
            "tool_success": "action_result",
            "tool_result_summary": "action_result",
            "trusted_known_facts": "incident_fact_profiles",
            "missing_required_facts": "incident_fact_profiles",
        },
    )
