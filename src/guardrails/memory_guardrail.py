"""
Memory Guardrail Module
Handles session memory key isolation (tenant_id:user_id:ticket_id) and prevents memory poisoning.
"""

import logging
from typing import Any

from src.guardrails.input_guardrails import detect_injection
from src.guardrails.output_guardrails import redact_secrets_and_pii

logger = logging.getLogger(__name__)


def generate_isolated_session_key(tenant_id: str, user_id: str, ticket_id: str) -> str:
    """Generate isolated multi-tenant session key."""
    tenant = tenant_id or "default_tenant"
    user = user_id or "anonymous"
    ticket = ticket_id or "general"
    return f"{tenant}:{user}:{ticket}"


def validate_memory_write(candidate_text: str) -> dict[str, Any]:
    """Validate candidate memory text against injection, secret leakage, and poisoning."""
    if not candidate_text:
        return {"allowed": False, "reason": "Empty candidate memory"}

    # 1. Injection scan
    inj_res = detect_injection(candidate_text)
    if inj_res["detected"]:
        return {"allowed": False, "reason": f"Memory write blocked due to prompt injection: {inj_res['reason']}"}

    # 2. Secret & PII check
    pii_res = redact_secrets_and_pii(candidate_text)
    if not pii_res["safe"]:
        return {"allowed": False, "reason": f"Memory write blocked due to secrets/PII: {pii_res['issues']}"}

    return {
        "allowed": True,
        "sanitized_memory": pii_res["redacted"],
        "reason": "Memory write validated successfully",
    }
