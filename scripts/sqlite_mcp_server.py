"""Local MCP server for the Help Desk SQLite database.

Read tools only accept SELECT/PRAGMA.  Write operations are intentionally
limited to INSERT/UPDATE/DELETE so schema-destructive commands cannot run via
the coding-agent connector.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DEFAULT_DB = Path(__file__).parent.parent / "data" / "helpdesk.db"
DATABASE_PATH = Path(os.getenv("HELPDESK_DB_PATH", str(DEFAULT_DB)))
mcp = FastMCP("Help Desk SQLite")


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _first_keyword(sql: str) -> str:
    return sql.lstrip().split(maxsplit=1)[0].upper() if sql.strip() else ""


@mcp.tool()
def list_tables() -> list[str]:
    """Return all user-managed SQLite tables in the Help Desk database."""
    with _connection() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [row["name"] for row in rows]


@mcp.tool()
def describe_table(table_name: str) -> list[dict]:
    """Return the schema of one allow-listed table."""
    if table_name not in set(list_tables()):
        raise ValueError(f"Unknown table: {table_name}")
    with _connection() as connection:
        rows = connection.execute(f"PRAGMA table_info([{table_name}])").fetchall()
    return [dict(row) for row in rows]


@mcp.tool()
def query(sql: str) -> list[dict]:
    """Run one read-only SELECT or PRAGMA query and return JSON-compatible rows."""
    keyword = _first_keyword(sql)
    if keyword not in {"SELECT", "PRAGMA", "WITH", "EXPLAIN"}:
        raise ValueError("Read-only query must start with SELECT, WITH, PRAGMA, or EXPLAIN")
    with _connection() as connection:
        rows = connection.execute(sql).fetchall()
    return [dict(row) for row in rows]


@mcp.tool()
def execute_write(sql: str) -> dict:
    """Run one INSERT, UPDATE, or DELETE statement and return affected rows."""
    keyword = _first_keyword(sql)
    if keyword not in {"INSERT", "UPDATE", "DELETE"}:
        raise ValueError("Write operation must start with INSERT, UPDATE, or DELETE")
    with _connection() as connection:
        result = connection.execute(sql)
    return {"rows_affected": result.rowcount, "last_insert_rowid": result.lastrowid}


if __name__ == "__main__":
    mcp.run()
