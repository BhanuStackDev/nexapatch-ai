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
    monkeypatch.setattr(agent_module, "DB_PATH", tmp_path / "quota-tests.db")
    monkeypatch.setattr(agent_module, "TARGET_REPO_PATH", tmp_path)
    monkeypatch.setattr(agent_module, "agent_graph", FakeGraph())
    monkeypatch.setattr(agent_module, "NEXAPATCH_API_TOKEN", "")
    monkeypatch.setattr(agent_module, "NEXAPATCH_ENV", "development")
    monkeypatch.setenv("NEXAPATCH_ENV", "development")
    monkeypatch.setenv("NEXAPATCH_SESSION_SECRET", "guest-quota-tests-session-secret-value-keep-long-123456789")
    monkeypatch.setenv("NEXAPATCH_FRONTEND_URL", FRONTEND_ORIGIN)
    monkeypatch.setenv("NEXAPATCH_GUEST_ANALYSES_PER_24H", "2")
    monkeypatch.setenv("NEXAPATCH_USER_ANALYSES_PER_24H", "4")
    monkeypatch.setenv("NEXAPATCH_GUEST_ACCESS_ENABLED", "true")


def _analyse(client: TestClient, task: str = "Inspect this repository safely."):
    return client.post(
        "/api/run-agent",
        headers={"Origin": FRONTEND_ORIGIN},
        json={"request_text": task},
    )


def _set_github_session(client: TestClient, user_id: int = 73142) -> None:
    session = {
        "version": 1,
        "issued_at": int(time.time()),
        "user": {"id": user_id, "login": "quota-test-user", "avatar_url": ""},
        "access_token": "test-only-access-token",
        "access_token_expires_at": None,
        "refresh_token": None,
        "refresh_token_expires_at": None,
    }
    response = JSONResponse({})
    github_auth._write_session_cookie(response, session)
    parsed = SimpleCookie()
    parsed.load(response.headers["set-cookie"])
    client.cookies.set(github_auth.SESSION_COOKIE, parsed[github_auth.SESSION_COOKIE].value)


def test_guest_quota_is_enforced_across_refresh_safe_cookie_requests(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    with TestClient(agent_module.app) as client:
        boot = client.get("/auth/me")
        assert boot.status_code == 200
        assert boot.json()["authenticated"] is False
        assert client.cookies.get(github_auth.GUEST_COOKIE)

        assert _analyse(client).status_code == 200
        assert _analyse(client, "Inspect the second repository safely.").status_code == 200
        limited = _analyse(client, "This third analysis must be blocked.")
        assert limited.status_code == 429
        assert "Guest analysis limit reached" in limited.json()["detail"]
        assert int(limited.headers["Retry-After"]) >= 1


def test_each_signed_guest_cookie_has_separate_history_and_quota(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    with TestClient(agent_module.app) as first_guest:
        first_guest.get("/auth/me")
        assert _analyse(first_guest).status_code == 200
        assert _analyse(first_guest, "Second first-guest analysis.").status_code == 200
        assert _analyse(first_guest, "Third first-guest analysis.").status_code == 429
        assert len(first_guest.get("/api/runs").json()["runs"]) == 2

        saved_cookie = first_guest.cookies.get(github_auth.GUEST_COOKIE)
        assert saved_cookie
        tampered_cookie = saved_cookie[:-1] + ("A" if saved_cookie[-1] != "A" else "B")
        request_stub = type(
            "RequestStub",
            (),
            {"cookies": {github_auth.GUEST_COOKIE: tampered_cookie}},
        )()
        assert github_auth._read_guest_identity(request_stub) is None

    with TestClient(agent_module.app) as second_guest:
        second_guest.get("/auth/me")
        assert _analyse(second_guest).status_code == 200
        assert len(second_guest.get("/api/runs").json()["runs"]) == 1


def test_github_user_uses_separate_configurable_quota(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv("NEXAPATCH_USER_ANALYSES_PER_24H", "2")
    with TestClient(agent_module.app) as client:
        _set_github_session(client)
        assert _analyse(client).status_code == 200
        assert _analyse(client, "Second signed-in analysis.").status_code == 200
        limited = _analyse(client, "Third signed-in analysis.")
        assert limited.status_code == 429
        assert "Account analysis limit reached" in limited.json()["detail"]


def test_guest_cookie_authenticated_post_rejects_bad_origin_in_production(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure(monkeypatch, tmp_path)
    monkeypatch.setattr(agent_module, "NEXAPATCH_ENV", "production")
    monkeypatch.setenv("NEXAPATCH_ENV", "production")
    with TestClient(agent_module.app) as client:
        response = client.post(
            "/api/run-agent",
            headers={"Origin": "https://attacker.example"},
            json={"request_text": "This request should be rejected."},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Request origin is not allowed."
