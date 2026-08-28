# Company Policy Engine migration

`scripts/migrate_policy_engine.py` is the only policy-core schema entry point. It is explicit, additive, and idempotent; normal application startup does not invoke it.

Use only an explicitly selected test or staging database:

```powershell
.\.venv\Scripts\python.exe scripts\migrate_policy_engine.py --database-url "sqlite+aiosqlite:///C:/safe/policy-test.db"
```

The migration creates only `policies`, `policy_versions`, `policy_scopes`, `policy_exceptions`, and `policy_audit_events`, their indexes, and SQLite immutability triggers. It never drops objects, seeds policies, changes Chroma, or modifies existing application rows. Validate backup/target identity before a production change; production execution is outside Phase 1C.1.
