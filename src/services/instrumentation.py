"""
Instrumentation Service — Micro-timing recorder using time.perf_counter()
Tracks stage-by-stage latency across the complete AI agent request path.
"""

import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional


class RequestTimer:
    """Lightweight stage timer for request path profiling."""

    def __init__(self, request_id: str = ""):
        self.request_id = request_id
        self.start_time = time.perf_counter()
        self.stages: Dict[str, float] = {}

    @contextmanager
    def time_stage(self, stage_name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            t1 = time.perf_counter()
            self.stages[stage_name] = round((t1 - t0) * 1000, 2)

    def mark_stage(self, stage_name: str, duration_ms: float):
        self.stages[stage_name] = round(duration_ms, 2)

    def get_summary(self) -> Dict[str, Any]:
        total_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        return {
            "request_id": self.request_id,
            "total_ms": total_ms,
            "stages": self.stages,
        }


def create_timer(request_id: str = "") -> RequestTimer:
    return RequestTimer(request_id)
