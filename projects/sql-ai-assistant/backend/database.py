import sqlite3
import os
import shutil
import logging
from typing import Any
from contextlib import contextmanager

from utils import timeit, safe_identifier

logger = logging.getLogger("sql_assistant.database")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

_db_path: str | None = None


def get_db_path() -> str | None:
    return _db_path


def set_db_path(path: str | None):
    global _db_path
    _db_path = path


@contextmanager
def get_connection():
    if not _db_path:
        raise RuntimeError("No database uploaded")
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_uploaded_db(file_bytes: bytes, filename: str) -> str:
    dest = os.path.join(UPLOAD_DIR, filename)
    with open(dest, "wb") as f:
        f.write(file_bytes)
    set_db_path(dest)
    logger.info(f"Database saved to {dest}")
    return dest


@timeit
def get_schema() -> list[dict[str, Any]]:
    tables = []
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        for row in cursor.fetchall():
            table_name = row["name"]
            col_cursor = conn.execute(f"PRAGMA table_info({safe_identifier(table_name)})")
            columns = [
                {"name": col["name"], "type": col["type"]}
                for col in col_cursor.fetchall()
            ]
            row_count = conn.execute(
                f"SELECT COUNT(*) FROM {safe_identifier(table_name)}"
            ).fetchone()[0]
            tables.append({
                "name": table_name,
                "columns": columns,
                "row_count": row_count,
            })
    return tables


def get_schema_text() -> str:
    tables = get_schema()
    lines = []
    for t in tables:
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
        lines.append(f"Table: {t['name']} ({t['row_count']} rows)")
        lines.append(f"  Columns: {cols}")
    return "\n".join(lines)


@timeit
def execute_query(sql: str) -> tuple[list[str], list[list[Any]], float]:
    import time
    start = time.perf_counter()
    with get_connection() as conn:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]
        elapsed = (time.perf_counter() - start) * 1000
    return columns, rows, elapsed


def get_tables_summary() -> list[dict[str, Any]]:
    tables = get_schema()
    return [
        {
            "name": t["name"],
            "column_count": len(t["columns"]),
            "row_count": t["row_count"],
            "columns": t["columns"],
        }
        for t in tables
    ]


def remove_db():
    global _db_path
    if _db_path and os.path.exists(_db_path):
        os.remove(_db_path)
        set_db_path(None)
        logger.info("Database removed")
