"""Offline, tenant-scoped exporter for already approved preference pairs."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import AsyncSessionLocal  # noqa: E402
from src.services.feedback_dataset_service import (  # noqa: E402
    dataset_quality_report,
    export_approved_preference_dataset,
)


async def _run(tenant_id: str, output_dir: Path | None) -> dict:
    async with AsyncSessionLocal() as db:
        report = await dataset_quality_report(db, tenant_id=tenant_id)
        if output_dir is not None:
            report["exported_sizes"] = await export_approved_preference_dataset(
                db, tenant_id=tenant_id, output_dir=output_dir
            )
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export approved, redacted preference data for one tenant")
    parser.add_argument("--tenant", required=True, help="Required tenant boundary; cross-tenant export is forbidden")
    parser.add_argument("--output-dir", type=Path, help="Write train/validation/test JSONL files")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_run(args.tenant, args.output_dir)), ensure_ascii=False, indent=2))
