"""Process-local datastore configuration shared by the pytest suite."""
import os

TEST_RUN_ID = str(os.getpid())

# These must be configured before importing application settings. The PID makes
# separately launched pytest processes—and xdist workers—own distinct SQLite
# and Chroma stores.
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./data/test-{TEST_RUN_ID}.db"
os.environ["CHROMA_PERSIST_DIR"] = f"./data/test_chroma-{TEST_RUN_ID}"
