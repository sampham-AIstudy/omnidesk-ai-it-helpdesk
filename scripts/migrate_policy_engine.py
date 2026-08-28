"""Explicitly create additive Company Policy Engine core tables on a chosen database."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import migrate_policy_engine_schema  # noqa: E402


async def main_async(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        await migrate_policy_engine_schema(engine)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True, help="Explicit test/staging target; no production default")
    args = parser.parse_args()
    asyncio.run(main_async(args.database_url))
