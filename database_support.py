"""Small SQLite/PostgreSQL adapter used by NexaPatch history and quota storage.

SQLite remains the default for local development/tests. Production deployments must
configure DATABASE_URL so ephemeral service filesystems are never treated as durable.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def is_postgresql_configured() -> bool:
    return bool(os.getenv("DATABASE_URL", "").strip())


def normalize_database_url(database_url: str) -> str:
    value = database_url.strip()
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    if not value.startswith("postgresql://"):
        raise ValueError("DATABASE_URL must use a postgresql:// or postgres:// URL.")
    return value


def adapt_sql(sql: str, *, is_postgres: bool) -> str:
    """Convert DB-API qmark placeholders to psycopg placeholders for PostgreSQL."""
    return sql.replace("?", "%s") if is_postgres else sql


class DatabaseConnection:
    """Minimal connection wrapper with a consistent execute/context-manager API."""

    def __init__(self, raw_connection: Any, *, is_postgres: bool) -> None:
        self._raw_connection = raw_connection
        self.is_postgres = is_postgres

    def execute(self, sql: str, parameters: Any = ()) -> Any:
        return self._raw_connection.execute(
            adapt_sql(sql, is_postgres=self.is_postgres), parameters
        )

    def commit(self) -> None:
        self._raw_connection.commit()

    def rollback(self) -> None:
        self._raw_connection.rollback()

    def close(self) -> None:
        self._raw_connection.close()

    def __enter__(self) -> "DatabaseConnection":
        return self

    def __exit__(self, exception_type: Any, exception: Any, traceback: Any) -> bool:
        try:
            if exception_type is None:
                self._raw_connection.commit()
            else:
                self._raw_connection.rollback()
        finally:
            self._raw_connection.close()
        return False


def connect_database(db_path: str | Path, timeout: float = 10) -> DatabaseConnection:
    """Connect to DATABASE_URL when configured; otherwise use local SQLite."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise sqlite3.OperationalError(
                "DATABASE_URL is configured but psycopg is not installed."
            ) from exc
        connection = psycopg.connect(
            normalize_database_url(database_url),
            connect_timeout=max(1, int(timeout)),
            row_factory=dict_row,
        )
        return DatabaseConnection(connection, is_postgres=True)

    environment = os.getenv("NEXAPATCH_ENV", "development").strip().lower()
    if environment in {"production", "prod"}:
        raise sqlite3.OperationalError(
            "DATABASE_URL must be configured in production. Refusing to use ephemeral SQLite storage."
        )

    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=timeout)
    connection.row_factory = sqlite3.Row
    return DatabaseConnection(connection, is_postgres=False)


def database_error_types() -> tuple[type[BaseException], ...]:
    """Return backend-specific database exception types for safe API handling."""
    errors: list[type[BaseException]] = [sqlite3.Error]
    if is_postgresql_configured():
        try:
            import psycopg
        except ImportError:
            return tuple(errors)
        errors.append(psycopg.Error)
    return tuple(errors)