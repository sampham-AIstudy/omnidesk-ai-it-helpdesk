"""One-time additive migration for the retired ``manager`` product role.

Run this explicitly against a copied/disposable database first.  It preserves
user IDs and tenant data while mapping only legacy role values to technician.
It does not run during application startup and never promotes users to admin.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def migrate_legacy_manager_roles(database: Path) -> tuple[int, int]:
    """Map legacy user and policy-scope role strings, idempotently."""
    with sqlite3.connect(database) as connection:
        users = connection.execute(
            "UPDATE users SET role = 'technician' WHERE role = 'manager'"
        ).rowcount
        scopes = connection.execute(
            "UPDATE policy_scopes SET role = 'technician' WHERE role = 'manager'"
        ).rowcount if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'policy_scopes'"
        ).fetchone() else 0
        connection.commit()
    return users, scopes


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy manager roles to technician.")
    parser.add_argument("database", type=Path, help="Explicit SQLite database path; production is never automatic.")
    args = parser.parse_args()
    users, scopes = migrate_legacy_manager_roles(args.database)
    print(f"Migrated {users} users and {scopes} policy scopes from manager to technician.")


if __name__ == "__main__":
    main()
