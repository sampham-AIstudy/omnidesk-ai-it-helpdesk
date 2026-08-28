# Feedback Pipeline Migration

The application uses additive SQLAlchemy/SQLite schema initialization rather than
Alembic. The feedback migration is **explicit-only**: normal application startup
does not create feedback tables. It creates `feedback_events` and
`preference_candidates`, required indexes, and append-only SQLite triggers. It may
add only `feedback_events.outcome_reason` and `preference_candidates.quality_tier`
to an already-created Phase 1 schema. It never alters ticket data or drops objects.

Test/staging invocation only:

```powershell
.\.venv\Scripts\python.exe scripts\migrate_feedback_pipeline.py --database-url "sqlite+aiosqlite:///C:/safe/test-feedback.db"
```

The command is idempotent. It also adds a one-way, auditable candidate-level
training exclusion (`excluded_from_training`, reason, actor, and timestamp) and
enforces that a reviewed candidate's status cannot change. Rollback is feature
rollback: disable feedback capture and leave the additive tables intact.
Dropping these audit records requires a separate explicitly authorized retention
procedure and is not part of this migration.
