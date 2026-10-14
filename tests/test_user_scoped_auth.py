"""Session-authenticated API and per-user history tests."""
from __future__ import annotations

import time
from http.cookies import SimpleCookie
from pathlib import Path

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import agent as agent_module
import github_auth

FRONTEND_ORIGIN = "http://localhost:5173"


class FakeGraph:
    async def ainvoke(self, state: dict[str, object]) -> dict[str, object]:
        return {
            "request_text": state["request_text"],
            "repo_root": state["repo_root"],
            "ai_used": True,
            "ai_error": "",
            "model": "test-model",
            "repository_summary": "A test repository.",
            "total_files_found": 1,
            "inventory_truncated": False,
            "discovered_files": ["main.py"],
            "files_in_context": ["main.py"],
            "execution_plan": "1. Inspect the repository safely.",
            "steps": ["Inspection completed"],
        }


def _configure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(agent_module, "DB_PATH", tmp_path / "auth-tests.db")
    monkeypatch.setattr(agent_module, "TARGET_REPO_PATH", tmp_path)
    monkeypatch.setattr(agent_module, "agent_graph", FakeGraph())
    monkeypatch.setattr(agent_module, "NEXAPATCH_API_TOKEN", "")
    monkeypatch.setattr(agent_module, "NEXAPATCH_ENV", "development")
    monkeypatch.setenv("NEXAPATCH_ENV", "development")
    monkeypatch.setenv("NEXAPATCH_SESSION_SECRET", "test-session-secret-for-nexapatch-only-987654")
    monkeypatch.setenv("NEXAPATCH_FRONTEND_URL", FRONTEND_ORIGIN)


def _set_session(client: TestClient, user_id: int, login: str) -> None:
    payload = {
        "version": 1,
        "issued_at": int(time.time()),
        "user": {"id": user_id, "login": login, "avatar_url": ""},
        "access_token": "test-only-access-token",
        "access_token_expires_at": None,
        "refresh_token": None,
        "refresh_token_expires_at": None,
    }
    response = JSONResponse({})
    github_auth._write_session_cookie(response, payload)
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    client.cookies.set(github_auth.SESSION_COOKIE, cookie[github_auth.SESSION_COOKIE].value)


def test_github_sessions_are_authenticated_and_history_is_user_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    with TestClient(agent_module.app) as client:
        _set_session(client, 10101, "alice-test")
        alice_response = client.post(
            "/api/run-agent",
            headers={"Origin": FRONTEND_ORIGIN},
            json={"request_text": "Inspect Alice's repository safely."},
        )
        assert alice_response.status_code == 200, alice_response.text
        assert len(client.get("/api/runs").json()["runs"]) == 1

        client.cookies.clear()
        _set_session(client, 20202, "bob-test")
        assert client.get("/api/runs").json()["runs"] == []

        bob_response = client.post(
            "/api/run-agent",
            headers={"Origin": FRONTEND_ORIGIN},
            json={"request_text": "Inspect Bob's repository safely."},
        )
        assert bob_response.status_code == 200, bob_response.text
        bob_runs = client.get("/api/runs").json()["runs"]
        assert len(bob_runs) == 1
        assert "Bob's" in bob_runs[0]["user_request"]

        client.cookies.clear()
        _set_session(client, 10101, "alice-test")
        alice_runs = client.get("/api/runs").json()["runs"]
        assert len(alice_runs) == 1
        assert "Alice's" in alice_runs[0]["user_request"]


def test_cookie_authenticated_post_rejects_untrusted_origin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    with TestClient(agent_module.app) as client:
        _set_session(client, 30303, "csrf-test")
        response = client.post(
            "/api/run-agent",
            headers={"Origin": "https://attacker.example"},
            json={"request_text": "Inspect this repository safely."},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Request origin is not allowed."


def test_old_database_rows_migrate_to_legacy_scope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import sqlite3

    database = tmp_path / "old-runs.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_request TEXT NOT NULL,
                workspace_name TEXT NOT NULL,
                discovered_files TEXT NOT NULL,
                files_in_context TEXT NOT NULL,
                execution_plan TEXT NOT NULL,
                status TEXT NOT NULL,
                model TEXT,
                created_at TEXT NOT NULL,
                language_mode TEXT NOT NULL DEFAULT 'auto',
                response_language TEXT NOT NULL DEFAULT 'auto'
            )"""
        )
        connection.execute(
            """INSERT INTO agent_runs (
                user_request, workspace_name, discovered_files, files_in_context,
                execution_plan, status, model, created_at, language_mode, response_language
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("old run", "old-workspace", "[]", "[]", "plan", "planned", "old-model", "2026-01-01T00:00:00+00:00", "auto", "auto"),
        )

    monkeypatch.setattr(agent_module, "DB_PATH", database)
    agent_module.init_database()
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)")}
        assert "user_id" in columns
        row = connection.execute("SELECT user_id FROM agent_runs WHERE id = 1").fetchone()
        assert row == ("legacy",)
