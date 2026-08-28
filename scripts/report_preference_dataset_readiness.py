"""Print a read-only feedback dataset sufficiency report; never trains or writes."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import get_settings  # noqa: E402
from src.services.feedback_dataset_service import dataset_readiness_report  # noqa: E402


def _readonly_sqlite_url(database_url: str) -> str:
    """Convert the configured SQLite path to an explicit read-only URI."""
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix) or "mode=ro" in database_url:
        return database_url
    path = database_url.removeprefix(prefix).replace("\\", "/")
    return f"sqlite+aiosqlite:///file:{path}?mode=ro&uri=true"


async def main_async(database_url: str, tenant_id: str | None) -> dict:
    engine = create_async_engine(_readonly_sqlite_url(database_url))
    try:
        async with engine.connect() as connection:
            table_names = await connection.run_sync(lambda conn: set(inspect(conn).get_table_names()))
        required = {"feedback_events", "preference_candidates"}
        if not required <= table_names:
            return {
                "migration_applied": False,
                "missing_tables": sorted(required - table_names),
                "DPO_DATA_READY": False,
                "ORPO_DATA_READY": False,
                "reasons": ["feedback_migration_not_applied"],
            }
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            report = await dataset_readiness_report(session, tenant_id=tenant_id)
            report["migration_applied"] = True
            return report
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=get_settings().database_url)
    parser.add_argument("--tenant", default=None, help="Required for tenant-scoped production reporting")
    args = parser.parse_args()
    result = asyncio.run(main_async(args.database_url, args.tenant))
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(serialized)
