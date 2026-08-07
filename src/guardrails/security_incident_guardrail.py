"""
Security Incident Guardrail Module
Detects security threats (phishing, compromise, malware, ransomware, data leak)
and forces SOC routing, HIGH priority, and zero auto-close.
"""

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)

SECURITY_KEYWORDS = [
    r"phishing", r"credential\s+theft", r"malware", r"ransomware",
    r"account\s+takeover", r"suspicious\s+login", r"data\s+leak",
    r"api\s+key\s+exposure", r"privilege\s+escalation", r"unauthorized\s+access",
    r"lừa\s+đảo", r"bị\s+hack", r"mã\s+độc", r"lộ\s+mật\s+khẩu"
]


def detect_security_incident(text: str) -> Dict[str, Any]:
    """Detect if request is a security incident."""
    if not text:
        return {"is_security_incident": False, "matched_keywords": []}

    matched = []
    for pattern in SECURITY_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(pattern)

    is_sec = len(matched) > 0
    return {
        "is_security_incident": is_sec,
        "matched_keywords": matched,
        "recommended_priority": "P1" if is_sec else "P3",
        "recommended_group": "SOC" if is_sec else "IT Support Tier 1",
        "disable_auto_close": is_sec,
        "reason": f"Security incident detected: {matched}" if is_sec else "Standard support ticket",
    }
