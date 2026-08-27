"""Phase 2 operational safety contracts for feedback preference collection."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database import Base, _create_application_schema_without_feedback, migrate_feedback_pipeline_schema
from src.models.ticket import Ticket, TicketStatus
from src.models.ticket_message import TicketMessage, TicketMessageSender
from src.models.user import CompanyUnit, User, UserRole
from src.services.feedback_dataset_service import (
    APPROVED,
    build_preference_candidates,
    dataset_readiness_report,
    export_approved_preference_dataset,
    record_ai_response_event,
    record_human_correction_event,
    record_ticket_outcome_event,
    record_ticket_rating_event,
    review_preference_candidate,
)


@pytest.fixture
async def db(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'phase2.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _ticket(db, tenant: CompanyUnit = CompanyUnit.REAL_ESTATE):
    user = User(username=f"p2-{tenant.value}", email=f"p2-{tenant.value}@example.invalid", full_name="P2", hashed_password="x", role=UserRole.EMPLOYEE, company_unit=tenant)
    db.add(user)
    await db.flush()
    ticket = Ticket(ticket_number=f"P2-{tenant.value}", title="VPN", description="VPN issue", submitter_id=user.id, status=TicketStatus.IN_PROGRESS)
    db.add(ticket)
    await db.flush()
    return user, ticket


@pytest.mark.asyncio
async def test_feedback_migration_is_idempotent_on_test_database(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'migration.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(_create_application_schema_without_feedback)
    await migrate_feedback_pipeline_schema(engine)
    await migrate_feedback_pipeline_schema(engine)
    async with engine.connect() as conn:
        names = {row[0] for row in (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))).all()}
        triggers = {row[0] for row in (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'"))).all()}
        indexes = await conn.run_sync(lambda sync_conn: {item["name"] for item in inspect(sync_conn).get_indexes("preference_candidates")})
    await engine.dispose()
    assert {"feedback_events", "preference_candidates"} <= names
    assert {"feedback_events_no_update", "feedback_events_no_delete", "preference_candidates_review_status_final"} <= triggers
    assert "ix_preference_candidates_quality_tier" in indexes


@pytest.mark.asyncio
async def test_explicit_provenance_rejects_invalid_cross_ticket_and_cross_tenant_ids(db):
    user, ticket = await _ticket(db)
    generation = await record_ai_response_event(db, tenant_id=user.company_unit.value, ticket_id=ticket.id, conversation_id=None, message_id="101", query="VPN?", answer="Use profile.", sources=[], model_provider="test", model_name="m", prompt_version="v1")
    await record_ticket_rating_event(db, tenant_id=user.company_unit.value, ticket_id=ticket.id, rating=4, comment="ok", actor_role="employee", answer_message_id=generation.message_id)
    with pytest.raises(ValueError):
        await record_ticket_rating_event(db, tenant_id=user.company_unit.value, ticket_id=ticket.id, rating=1, comment="bad", actor_role="employee", answer_message_id="404")
    other_user, other_ticket = await _ticket(db, CompanyUnit.AUTOMOTIVE)
    with pytest.raises(ValueError):
        await record_ticket_rating_event(db, tenant_id=other_user.company_unit.value, ticket_id=other_ticket.id, rating=1, comment="bad", actor_role="employee", answer_message_id=generation.message_id)
    legacy = await record_ticket_rating_event(db, tenant_id=user.company_unit.value, ticket_id=ticket.id, rating=3, comment="legacy", actor_role="employee")
    assert legacy.target_event_id is None


@pytest.mark.asyncio
async def test_explicit_correction_is_high_tier_and_manifest_is_stable(db, tmp_path):
    user, ticket = await _ticket(db)
    generation = await record_ai_response_event(db, tenant_id=user.company_unit.value, ticket_id=ticket.id, conversation_id=None, message_id="102", query="VPN?", answer="Disable security.", sources=[{"source_id": "kb-1", "source_type": "internal_kb"}], model_provider="test", model_name="m", prompt_version="v1")
    correction_message = TicketMessage(ticket_id=ticket.id, sender_type=TicketMessageSender.TECHNICIAN, content="Use the approved VPN profile.")
    db.add(correction_message)
    await db.flush()
    await record_human_correction_event(db, tenant_id=user.company_unit.value, ticket_id=ticket.id, message=correction_message, actor_role="technician", answer_message_id=generation.message_id)
    await record_ticket_outcome_event(db, tenant_id=user.company_unit.value, ticket_id=ticket.id, outcome="reopened", actor_role="employee", answer_message_id=generation.message_id, reason="Still failing")
    candidate = (await build_preference_candidates(db, tenant_id=user.company_unit.value))[0]
    assert candidate.quality_tier == "HIGH"
    manager = User(username="p2-manager", email="p2-manager@example.invalid", full_name="Manager", hashed_password="x", role=UserRole.MANAGER, company_unit=user.company_unit)
    employee = User(username="p2-employee", email="p2-employee@example.invalid", full_name="Employee", hashed_password="x", role=UserRole.EMPLOYEE, company_unit=user.company_unit)
    db.add_all([manager, employee])
    await db.flush()
    with pytest.raises(PermissionError):
        await review_preference_candidate(db, candidate_id=candidate.candidate_id, reviewer=employee, status=APPROVED)
    other_manager = User(username="p2-other-manager", email="p2-other-manager@example.invalid", full_name="Other", hashed_password="x", role=UserRole.MANAGER, company_unit=CompanyUnit.AUTOMOTIVE)
    db.add(other_manager)
    await db.flush()
    with pytest.raises(PermissionError, match="tenant"):
        await review_preference_candidate(db, candidate_id=candidate.candidate_id, reviewer=other_manager, status=APPROVED)
    await review_preference_candidate(db, candidate_id=candidate.candidate_id, reviewer=manager, status=APPROVED)
    first, second = tmp_path / "first", tmp_path / "second"
    await export_approved_preference_dataset(db, tenant_id=user.company_unit.value, output_dir=first)
    await export_approved_preference_dataset(db, tenant_id=user.company_unit.value, output_dir=second)
    a, b = json.loads((first / "manifest.json").read_text()), json.loads((second / "manifest.json").read_text())
    assert a["content_hash"] == b["content_hash"]
    assert a["record_count"] == 1 and a["source_event_count"] == 2


@pytest.mark.asyncio
async def test_readiness_handles_empty_data_and_requires_tenant_scope(db):
    empty = await dataset_readiness_report(db, tenant_id=CompanyUnit.REAL_ESTATE.value)
    assert empty["DPO_DATA_READY"] is False
    assert empty["ORPO_DATA_READY"] is False
    assert "no_approved_real_preference_pairs" in empty["reasons"]
    aggregate = await dataset_readiness_report(db)
    assert "tenant_scope_required_for_training_dataset" in aggregate["reasons"]
