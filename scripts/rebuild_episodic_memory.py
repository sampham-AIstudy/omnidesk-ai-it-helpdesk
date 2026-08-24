"""Rebuild the Zero-Mem ticket/conversation index from authoritative SQL records."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow the documented `python scripts/rebuild_episodic_memory.py` invocation.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import AsyncSessionLocal, init_db
from src.services.zero_mem_service import rebuild_episodic_memory_index


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        count = await rebuild_episodic_memory_index(db)
        await db.commit()
    print(f"Indexed {count} Zero-Mem provenance traces.")


if __name__ == "__main__":
    asyncio.run(main())
