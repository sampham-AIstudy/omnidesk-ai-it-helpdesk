from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from src.database import _create_application_schema_without_feedback, migrate_policy_engine_schema
from src.models import policy  # noqa: F401


@pytest.mark.asyncio
async def test_policy_migration_is_explicit_and_idempotent(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'policy.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(_create_application_schema_without_feedback)
    await migrate_policy_engine_schema(engine)
    await migrate_policy_engine_schema(engine)
    async with engine.connect() as conn:
        tables = {row[0] for row in (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))).all()}
        triggers = {row[0] for row in (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'"))).all()}
    await engine.dispose()
    assert {"policies", "policy_versions", "policy_scopes", "policy_exceptions", "policy_audit_events"} <= tables
    assert {"policy_versions_immutable_after_approval", "policy_audit_events_no_update", "policy_audit_events_no_delete"} <= triggers


@pytest.mark.asyncio
async def test_sqlite_policy_immutability_triggers_reject_direct_mutations(tmp_path):
    """Direct SQL must be rejected even when ORM event hooks are bypassed."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'immutability.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(_create_application_schema_without_feedback)
    await migrate_policy_engine_schema(engine)
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO policies (id, policy_key, tenant_id, name, category, status) VALUES ('p', 'P', 'automotive', 'Policy', 'security', 'active')"))
        for version_id, number, status in (("approved", 1, "approved"), ("active", 2, "active")):
            await conn.execute(text("INSERT INTO policy_versions (id, policy_id, version_number, title, content, rule_definition_json, effect_summary, priority, effective_from, status, content_hash) VALUES (:id, 'p', :number, 'title', 'content', '{}', 'summary', 1, '2026-01-01 00:00:00', :status, 'hash')"), {"id": version_id, "number": number, "status": status})
        await conn.execute(text("INSERT INTO policy_audit_events (id, tenant_id, event_type, metadata_json) VALUES ('audit', 'automotive', 'enforcement', '{}')"))

        for statement in (
            "UPDATE policy_versions SET title = 'changed' WHERE id = 'approved'",
            "UPDATE policy_versions SET title = 'changed' WHERE id = 'active'",
            "DELETE FROM policy_versions WHERE id = 'approved'",
            "DELETE FROM policy_versions WHERE id = 'active'",
            "UPDATE policy_audit_events SET event_type = 'changed' WHERE id = 'audit'",
            "DELETE FROM policy_audit_events WHERE id = 'audit'",
        ):
            with pytest.raises(IntegrityError):
                async with conn.begin_nested():
                    await conn.execute(text(statement))
    await engine.dispose()
