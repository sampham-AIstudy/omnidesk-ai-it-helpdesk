"""
Monitoring & Alerts Module
Tracks system metrics (block_rate, HITL_rate, unsafe_output_rate) and triggers alerts.
Thresholds: BLOCK_RATE_THRESHOLD=0.5, JUDGE_FAIL_RATE_THRESHOLD=0.3.
"""

import json
import logging
from pathlib import Path
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MetricsTracker:
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "sanitized_requests": 0,
            "prompt_injection_count": 0,
            "PII_leak_count": 0,
            "secret_leak_count": 0,
            "rate_limit_hits": 0,
            "RAG_injection_count": 0,
            "tool_denials": 0,
            "HITL_count": 0,
            "auto_close_count": 0,
            "routing_review_count": 0,
            "security_incident_count": 0,
            "judge_failure_count": 0,
            "groundedness_failure_count": 0,
            "SLA_escalation_count": 0,
        }

    def record(self, metric_name: str, count: int = 1):
        if metric_name in self.metrics:
            self.metrics[metric_name] += count

    def get_summary(self) -> dict[str, Any]:
        total = max(self.metrics["total_requests"], 1)
        block_rate = round(self.metrics["blocked_requests"] / total, 2)
        hitl_rate = round(self.metrics["HITL_count"] / total, 2)
        judge_fail_rate = round(self.metrics["judge_failure_count"] / total, 2)

        alerts = []
        if block_rate > settings.block_rate_threshold:
            alerts.append(f"HIGH BLOCK RATE ALERT: {block_rate:.2f} > {settings.block_rate_threshold}")
        if judge_fail_rate > settings.judge_fail_rate_threshold:
            alerts.append(f"HIGH SAFETY JUDGE FAIL RATE ALERT: {judge_fail_rate:.2f} > {settings.judge_fail_rate_threshold}")

        summary = {
            "raw_metrics": self.metrics,
            "block_rate": block_rate,
            "hitl_rate": hitl_rate,
            "judge_fail_rate": judge_fail_rate,
            "alerts": alerts,
        }
        return summary

    def export_json(self, output_path: str = "outputs/metrics.json"):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.get_summary(), f, indent=2, ensure_ascii=False)
        logger.info(f"Exported security metrics to {output_path}")


_global_tracker = MetricsTracker()


def get_metrics_tracker() -> MetricsTracker:
    return _global_tracker
