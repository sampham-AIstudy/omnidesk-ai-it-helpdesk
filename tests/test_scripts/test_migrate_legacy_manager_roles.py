import sqlite3
from pathlib import Path

from scripts.migrate_legacy_manager_roles import migrate_legacy_manager_roles


def test_legacy_manager_migration_is_idempotent_and_preserves_rows(tmp_path: Path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, role TEXT, company_unit TEXT);
            CREATE TABLE policy_scopes (id INTEGER PRIMARY KEY, role TEXT);
            INSERT INTO users VALUES (7, 'manager', 'automotive');
            INSERT INTO users VALUES (8, 'admin', 'corporate');
            INSERT INTO policy_scopes VALUES (11, 'manager');
        """)
    assert migrate_legacy_manager_roles(database) == (1, 1)
    assert migrate_legacy_manager_roles(database) == (0, 0)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, role, company_unit FROM users WHERE id = 7").fetchone() == (7, "technician", "automotive")
        assert connection.execute("SELECT role FROM users WHERE id = 8").fetchone() == ("admin",)
        assert connection.execute("SELECT role FROM policy_scopes WHERE id = 11").fetchone() == ("technician",)
