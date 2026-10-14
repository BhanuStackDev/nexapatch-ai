from __future__ import annotations

import sqlite3

import pytest

from database_support import (
    adapt_sql,
    connect_database,
    normalize_database_url,
)


def test_sql_adapter_keeps_sqlite_placeholders() -> None:
    query = "SELECT * FROM entries WHERE owner = ? AND created_at > ?"
    assert adapt_sql(query, is_postgres=False) == query


def test_sql_adapter_converts_qmark_placeholders_for_postgres() -> None:
    query = "SELECT * FROM entries WHERE owner = ? AND created_at > ?"
    assert adapt_sql(query, is_postgres=True) == (
        "SELECT * FROM entries WHERE owner = %s AND created_at > %s"
    )


def test_legacy_postgres_url_scheme_is_normalized() -> None:
    assert normalize_database_url("postgres://user:password@localhost/example") == (
        "postgresql://user:password@localhost/example"
    )


def test_sqlite_connection_supports_rows_and_closes_after_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("NEXAPATCH_ENV", raising=False)
    database_path = tmp_path / "nested" / "runs.sqlite3"

    with connect_database(database_path) as connection:
        assert not connection.is_postgres
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, label TEXT NOT NULL)")
        connection.execute("INSERT INTO sample(label) VALUES (?)", ("kept",))
        row = connection.execute("SELECT id, label FROM sample").fetchone()
        assert row["label"] == "kept"
        assert dict(row) == {"id": 1, "label": "kept"}

    raw = sqlite3.connect(database_path)
    try:
        assert raw.execute("SELECT label FROM sample").fetchone()[0] == "kept"
    finally:
        raw.close()


def test_production_refuses_ephemeral_sqlite_without_database_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("NEXAPATCH_ENV", "production")
    with pytest.raises(sqlite3.OperationalError, match="DATABASE_URL must be configured"):
        connect_database(tmp_path / "must-not-be-created.sqlite3")
    assert not (tmp_path / "must-not-be-created.sqlite3").exists()