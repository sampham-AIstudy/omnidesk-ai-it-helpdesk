"""One-way, auditable exclusion of a retained preference candidate.

This is intentionally separate from the ordinary exporter: it never deletes
source events, never changes a human review status, and never creates a
dataset.  The caller must name the exact candidate and the operational reason.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.feedback_dataset_service import exclude_preference_candidate_from_training  # noqa: E402


async def main_async(database_url: str, candidate_id: str, reason: str, actor: str) -> dict[str, str | bool | None]:
    engine = create_async_engine(database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            candidate = await exclude_preference_candidate_from_training(
                session,
                candidate_id=candidate_id,
                reason=reason,
                excluded_by=actor,
            )
            await session.commit()
            return {
                "candidate_id": candidate.candidate_id,
                "tenant_id": candidate.tenant_id,
                "review_status": candidate.review_status,
                "excluded_from_training": candidate.excluded_from_training,
                "training_exclusion_reason": candidate.training_exclusion_reason,
                "training_excluded_by": candidate.training_excluded_by,
                "training_excluded_at": candidate.training_excluded_at.isoformat() if candidate.training_excluded_at else None,
            }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True, help="Explicit database URL; no default production target")
    parser.add_argument("--candidate-id", required=True, help="Exact retained candidate to exclude")
    parser.add_argument("--reason", required=True, help="Auditable operational exclusion reason")
    parser.add_argument("--actor", required=True, help="Operator or change-control identifier")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(main_async(args.database_url, args.candidate_id, args.reason, args.actor)), ensure_ascii=False, indent=2))
