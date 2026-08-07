"""
SQLAlchemy async database engine + session factory.
"""
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings

settings = get_settings()

# Ensure data directory exists
Path("./data").mkdir(exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    connect_args={"check_same_thread": False, "timeout": 15} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency injection: yield DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


from sqlalchemy import event, text

# SQLite PRAGMA Listener (Enforce FKs, WAL mode, and busy timeout on every connection)
@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA foreign_keys=ON")
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        cursor.close()


def _auto_migrate_sqlite(connection):
    """Tự động bổ sung cột mới cho DB SQLite cũ mà không cần xóa DB."""
    try:
        # 1. Tickets table columns
        res_t = connection.execute(text("PRAGMA table_info(tickets)"))
        t_cols = {row[1] for row in res_t.fetchall()}
        if t_cols:
            new_ticket_cols = {
                "support_mode": "VARCHAR(20) DEFAULT 'AI'",
                "closed_by": "VARCHAR(50)",
                "resolution_summary": "TEXT",
                "rating": "INTEGER",
                "rating_feedback": "TEXT",
                "closed_at": "DATETIME",
                "reopened_at": "DATETIME",
                "classification_confidence": "FLOAT",
                "retrieval_confidence": "FLOAT",
                "groundedness_score": "FLOAT",
                "decision_summary": "TEXT",
                "decision_factors_json": "TEXT",
            }
            for col_name, col_type in new_ticket_cols.items():
                if col_name not in t_cols:
                    connection.execute(text(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}"))

        # 2. Audit logs trace_id
        res_a = connection.execute(text("PRAGMA table_info(audit_logs)"))
        a_cols = {row[1] for row in res_a.fetchall()}
        if a_cols and "trace_id" not in a_cols:
            connection.execute(text("ALTER TABLE audit_logs ADD COLUMN trace_id VARCHAR(64)"))

        # 3. Knowledge base version columns
        res_k = connection.execute(text("PRAGMA table_info(knowledge_base)"))
        k_cols = {row[1] for row in res_k.fetchall()}
        if k_cols:
            kb_new_cols = {
                "version": "INTEGER DEFAULT 1",
                "content_hash": "VARCHAR(64)",
                "effective_from": "DATETIME",
                "effective_to": "DATETIME",
            }
        # 4. Hitl approvals columns
        res_h = connection.execute(text("PRAGMA table_info(hitl_approvals)"))
        h_cols = {row[1] for row in res_h.fetchall()}
        if h_cols:
            hitl_new_cols = {
                "action_type": "VARCHAR(50) DEFAULT 'EXECUTE_HIGH_RISK'",
                "action_payload": "TEXT",
                "risk_score": "FLOAT DEFAULT 0.0",
            }
            for col_name, col_type in hitl_new_cols.items():
                if col_name not in h_cols:
                    connection.execute(text(f"ALTER TABLE hitl_approvals ADD COLUMN {col_name} {col_type}"))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("SQLite auto migration note: %s", exc)


async def init_db():
    """Create all tables and perform lightweight SQLite column migration."""
    from src.models import (  # noqa: F401
        ai_run,
        audit_log,
        hitl_approval,
        knowledge_base,
        ticket,
        ticket_message,
        user,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_auto_migrate_sqlite)

