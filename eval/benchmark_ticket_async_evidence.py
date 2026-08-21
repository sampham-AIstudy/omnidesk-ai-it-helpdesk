"""Focused, reproducible benchmark for ticket KB + Zero-Mem acquisition.

This intentionally benchmarks only the dependency-safe evidence phase with
controlled I/O boundaries.  It proves scheduling overlap without representing
provider, Chroma, SQLite, web, or LLM production latency as measured data.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCENARIOS = {
    "ticket_simple_kb": (0.040, 0.010),
    "ticket_kb_relevant_memory": (0.060, 0.060),
    "ticket_kb_irrelevant_memory": (0.060, 0.035),
    "ticket_weak_kb_web_fallback_pre_web": (0.050, 0.050),
    "ticket_direct_or_hitl_shortcut": (0.000, 0.000),
    "ticket_multiturn_contextual": (0.060, 0.060),
}


def _ticket() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        category=None,
        submitter=SimpleNamespace(
            company_unit=SimpleNamespace(value="corporate"), department="IT",
        ),
    )


def _percentile(values: list[float], percentile: int) -> float:
    if len(values) == 1:
        return values[0]
    return quantiles(values, n=100, method="inclusive")[percentile - 1]


async def _parallel_once(kb_delay: float, memory_delay: float) -> float:
    if not kb_delay and not memory_delay:
        return 0.0

    async def kb_turn(queries, retrieve):
        await asyncio.sleep(kb_delay)
        return SimpleNamespace(results=[SimpleNamespace(documents=[], outcome="EMPTY")])

    async def memory_lookup(*args, **kwargs):
        await asyncio.sleep(memory_delay)
        return [], {"enabled": True, "evidence_final_count": 0}

    from src.services import ticket_conversation_service as conversation

    started = perf_counter()
    with (
        patch.object(conversation, "retrieve_turn_with_bounded_retry", kb_turn),
        patch("src.services.zero_mem_service.retrieve_episodic_evidence", memory_lookup),
    ):
        await conversation._acquire_ticket_evidence(
            object(), query="bounded benchmark", ticket=_ticket(), user=object(),
        )
    return (perf_counter() - started) * 1000


async def _serial_once(kb_delay: float, memory_delay: float) -> float:
    started = perf_counter()
    await asyncio.sleep(kb_delay)
    await asyncio.sleep(memory_delay)
    return (perf_counter() - started) * 1000


async def _measure(name: str, kb_delay: float, memory_delay: float, repetitions: int) -> dict[str, object]:
    cold_before = await _serial_once(kb_delay, memory_delay)
    cold_after = await _parallel_once(kb_delay, memory_delay)
    before = [await _serial_once(kb_delay, memory_delay) for _ in range(repetitions)]
    after = [await _parallel_once(kb_delay, memory_delay) for _ in range(repetitions)]
    return {
        "scenario": name,
        "scope": "controlled_evidence_acquisition_only",
        "configured_kb_delay_ms": kb_delay * 1000,
        "configured_memory_delay_ms": memory_delay * 1000,
        "cold_before_ms": round(cold_before, 2),
        "cold_after_ms": round(cold_after, 2),
        "warm_before_p50_ms": round(median(before), 2),
        "warm_after_p50_ms": round(median(after), 2),
        "warm_before_p95_ms": round(_percentile(before, 95), 2),
        "warm_after_p95_ms": round(_percentile(after, 95), 2),
        "warm_p50_delta_ms": round(median(after) - median(before), 2),
        "warm_p95_delta_ms": round(_percentile(after, 95) - _percentile(before, 95), 2),
    }


async def _main(repetitions: int) -> list[dict[str, object]]:
    return [
        await _measure(name, kb_delay, memory_delay, repetitions)
        for name, (kb_delay, memory_delay) in SCENARIOS.items()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=20)
    args = parser.parse_args()
    if args.repetitions < 5:
        parser.error("--repetitions must be at least 5")
    print(json.dumps({
        "environment": "controlled asyncio sleep boundaries; no Chroma, SQLite, web, or LLM timing",
        "repetitions": args.repetitions,
        "results": asyncio.run(_main(args.repetitions)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
