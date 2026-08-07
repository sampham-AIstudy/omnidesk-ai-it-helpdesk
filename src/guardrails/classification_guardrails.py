"""
Classification Guardrail Module
Evaluates ticket classification confidence (Category, Priority P1-P4, Urgency, Routing Assignment).
High Confidence >= 0.90, Medium 0.70-0.89, Low < 0.70 (forces HITL).
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def evaluate_classification_confidence(classification: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate classification confidence against thresholds."""
    cat_conf = classification.get("category_confidence", 1.0)
    prio_conf = classification.get("priority_confidence", 1.0)
    urg_conf = classification.get("urgency_confidence", 1.0)
    route_conf = classification.get("routing_confidence", 1.0)

    min_confidence = min(cat_conf, prio_conf, urg_conf, route_conf)

    if min_confidence >= 0.90:
        level = "HIGH"
        requires_hitl = False
    elif min_confidence >= 0.70:
        level = "MEDIUM"
        requires_hitl = False
    else:
        level = "LOW"
        requires_hitl = True

    return {
        "level": level,
        "min_confidence": min_confidence,
        "requires_hitl": requires_hitl,
        "reason": f"Classification confidence level {level} ({min_confidence:.2f})",
    }
