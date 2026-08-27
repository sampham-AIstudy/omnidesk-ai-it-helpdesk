"""
SQLAlchemy async database engine + session factory.
"""
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings

settings = get_settings()

# Ensure data directory exists
Path("./data").mkdir(exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    # SQL echo includes bound values and ticket/KB text; SQLAlchemy spans record
    # operation metadata instead, never raw statements or parameters.
    echo=False,
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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection: yield DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


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
        # 0. Personal profile fields.  This remains on the authenticated User
        # record, so it is naturally scoped by the JWT-backed /auth/me API.
        res_u = connection.execute(text("PRAGMA table_info(users)"))
        u_cols = {row[1] for row in res_u.fetchall()}
        if u_cols and "phone" not in u_cols:
            connection.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(30)"))
        if u_cols:
            # Enum columns created by older SQLAlchemy metadata used enum names
            # (for example EMPLOYEE).  Persist values in the same lowercase
            # representation the API and frontend use.
            connection.execute(text("UPDATE users SET role = LOWER(role), company_unit = LOWER(company_unit)"))

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
                "duplicate_of_ticket_id": "INTEGER",
                "duplicate_score": "FLOAT",
                "duplicate_detection_method": "VARCHAR(50)",
                "duplicate_confirmed_by": "VARCHAR(100)",
                "parent_incident_ticket_id": "INTEGER",
                "is_pinned": "BOOLEAN DEFAULT 0",
                "pinned_by_id": "INTEGER",
                "pinned_at": "DATETIME",
                "pin_reason": "VARCHAR(255)",
            }
            for col_name, col_type in new_ticket_cols.items():
                if col_name not in t_cols:
                    connection.execute(text(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}"))
            connection.execute(text("UPDATE tickets SET status = LOWER(status), category = LOWER(category), priority = LOWER(priority), urgency = LOWER(urgency), support_mode = LOWER(support_mode)"))
            # Cover the most frequent employee list and ticket-detail lookups.
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_submitter_created_at ON tickets (submitter_id, created_at DESC)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_duplicate_of ON tickets (duplicate_of_ticket_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_parent_incident ON tickets (parent_incident_ticket_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_pinned ON tickets (is_pinned, created_at DESC)"))

        # 1b. Ticket messages table
        res_m = connection.execute(text("PRAGMA table_info(ticket_messages)"))
        m_cols = {row[1] for row in res_m.fetchall()}
        if m_cols and "is_internal" not in m_cols:
            connection.execute(text("ALTER TABLE ticket_messages ADD COLUMN is_internal BOOLEAN DEFAULT 0"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_ticket_messages_internal ON ticket_messages (ticket_id, is_internal)"))

        # 2. Audit logs trace_id
        res_a = connection.execute(text("PRAGMA table_info(audit_logs)"))
        a_cols = {row[1] for row in res_a.fetchall()}
        if a_cols and "trace_id" not in a_cols:
            connection.execute(text("ALTER TABLE audit_logs ADD COLUMN trace_id VARCHAR(64)"))
        if a_cols:
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_ticket_created ON audit_logs (ticket_id, created_at DESC)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_action_created ON audit_logs (action, created_at DESC)"))
            if "service_request_id" not in a_cols:
                connection.execute(text("ALTER TABLE audit_logs ADD COLUMN service_request_id INTEGER"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_service_request_created ON audit_logs (service_request_id, created_at DESC)"))

        # 2c. Service Request fulfillment ownership and completion dates.
        res_sr = connection.execute(text("PRAGMA table_info(service_requests)"))
        sr_cols = {row[1] for row in res_sr.fetchall()}
        if sr_cols:
            sr_new_cols = {
                "assignee_id": "INTEGER",
                "assigned_at": "DATETIME",
                "fulfilled_at": "DATETIME",
                "fulfilled_by_id": "INTEGER",
                "approval_comment": "TEXT",
                "approved_by_id": "INTEGER",
                "approved_at": "DATETIME",
                "rejected_by_id": "INTEGER",
                "rejected_at": "DATETIME",
            }
            for col_name, col_type in sr_new_cols.items():
                if col_name not in sr_cols:
                    connection.execute(text(f"ALTER TABLE service_requests ADD COLUMN {col_name} {col_type}"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_service_requests_group_status_created ON service_requests (fulfillment_group, status, created_at, id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_service_requests_assignee_status ON service_requests (assignee_id, status)"))

        # 2b. The FTS table is an index only; raw ticket/message text remains
        # authoritative.  SQLite builds without FTS5 simply use dense+entity retrieval.
        try:
            connection.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS episodic_memory_fts USING fts5(trace_id UNINDEXED, tenant_id UNINDEXED, department UNINDEXED, owner_user_id UNINDEXED, content)"))
        except Exception as fts_exc:
            logging.getLogger(__name__).warning("SQLite FTS5 unavailable for episodic memory: %s", fts_exc)

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
            for col_name, col_type in kb_new_cols.items():
                if col_name not in k_cols:
                    connection.execute(text(f"ALTER TABLE knowledge_base ADD COLUMN {col_name} {col_type}"))
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
        # 5. Bảng token_usage_logs (tạo qua create_all; migration bổ sung thêm index)
        res_tul = connection.execute(text("PRAGMA table_info(token_usage_logs)"))
        tul_cols = {row[1] for row in res_tul.fetchall()}
        if tul_cols:
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_token_usage_user_created ON token_usage_logs (user_id, created_at DESC)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_token_usage_model_created ON token_usage_logs (model_name, created_at DESC)"))

        # 6. Feedback pipeline fields introduced after the initial append-only
        # tables.  Additive only: existing tickets and event rows are never
        # rewritten or removed.
        res_feedback = connection.execute(text("PRAGMA table_info(feedback_events)"))
        feedback_cols = {row[1] for row in res_feedback.fetchall()}
        if feedback_cols and "outcome_reason" not in feedback_cols:
            connection.execute(text("ALTER TABLE feedback_events ADD COLUMN outcome_reason TEXT"))
        res_candidate = connection.execute(text("PRAGMA table_info(preference_candidates)"))
        candidate_cols = {row[1] for row in res_candidate.fetchall()}
        if candidate_cols and "quality_tier" not in candidate_cols:
            connection.execute(text("ALTER TABLE preference_candidates ADD COLUMN quality_tier VARCHAR(10) NOT NULL DEFAULT 'LOW'"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_preference_candidates_quality_tier ON preference_candidates (quality_tier)"))
        if candidate_cols and "excluded_from_training" not in candidate_cols:
            connection.execute(text("ALTER TABLE preference_candidates ADD COLUMN excluded_from_training BOOLEAN NOT NULL DEFAULT 0"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_preference_candidates_excluded_from_training ON preference_candidates (excluded_from_training)"))
        if candidate_cols and "training_exclusion_reason" not in candidate_cols:
            connection.execute(text("ALTER TABLE preference_candidates ADD COLUMN training_exclusion_reason VARCHAR(160)"))
        if candidate_cols and "training_excluded_by" not in candidate_cols:
            connection.execute(text("ALTER TABLE preference_candidates ADD COLUMN training_excluded_by VARCHAR(80)"))
        if candidate_cols and "training_excluded_at" not in candidate_cols:
            connection.execute(text("ALTER TABLE preference_candidates ADD COLUMN training_excluded_at DATETIME"))
    except Exception as exc:
        logging.getLogger(__name__).warning("SQLite auto migration note: %s", exc)


async def init_db():
    """Create application tables, excluding explicitly approved feedback migrations."""
    from src.models import (  # noqa: F401
        ai_run,
        audit_log,
        chat_conversation,
        episodic_memory,
        feedback_event,
        hitl_approval,
        knowledge_base,
        knowledge_gap,
        preference_candidate,
        service_request,
        technician_fulfillment_group,
        ticket,
        ticket_message,
        token_usage,
        user,
        web_research,
    )

    async with engine.begin() as conn:
        await conn.run_sync(_create_application_schema_without_feedback)
        await conn.run_sync(_auto_migrate_sqlite)


def _create_application_schema_without_feedback(connection) -> None:
    """Keep additive feedback tables behind the explicit migration command.

    This prevents a normal production service restart from changing the
    database. Test/staging (and a separately approved production rollout) use
    ``migrate_feedback_pipeline_schema`` instead.
    """
    feedback_tables = {"feedback_events", "preference_candidates"}
    tables = [
        table for name, table in Base.metadata.tables.items() if name not in feedback_tables
    ]
    Base.metadata.create_all(connection, tables=tables)


def _migrate_feedback_pipeline_schema(connection) -> None:
    """Create/upgrade feedback tables without destructive schema operations."""
    from src.models.feedback_event import FeedbackEvent
    from src.models.preference_candidate import PreferenceCandidate

    FeedbackEvent.__table__.create(connection, checkfirst=True)
    PreferenceCandidate.__table__.create(connection, checkfirst=True)
    if connection.dialect.name == "sqlite":
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS feedback_events_no_update BEFORE UPDATE ON feedback_events BEGIN SELECT RAISE(ABORT, 'feedback_events are immutable'); END"))
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS feedback_events_no_delete BEFORE DELETE ON feedback_events BEGIN SELECT RAISE(ABORT, 'feedback_events are append-only'); END"))
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS preference_candidates_review_status_final BEFORE UPDATE OF review_status ON preference_candidates WHEN OLD.review_status != 'PENDING_REVIEW' BEGIN SELECT RAISE(ABORT, 'reviewed preference candidate status is immutable'); END"))


async def migrate_feedback_pipeline_schema(target_engine) -> None:
    """Idempotent migration entry point for an explicitly selected database."""
    async with target_engine.begin() as conn:
        await conn.run_sync(_migrate_feedback_pipeline_schema)
        if conn.dialect.name == "sqlite":
            await conn.run_sync(_auto_migrate_sqlite)
