from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

import agent
import github_auth


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, *, headers=None, data=None, **kwargs):
        if data and data.get("grant_type") == "refresh_token":
            return FakeResponse({
                "access_token": "test-access-token-refreshed",
                "expires_in": 3600,
                "refresh_token": "test-refresh-token-rotated",
                "refresh_token_expires_in": 15_000_000,
            })
        assert url == github_auth.GITHUB_TOKEN_URL
        assert data["client_id"] == "test-client-id"
        assert data["code_verifier"]
        return FakeResponse({
            "access_token": "test-access-token",
            "expires_in": 3600,
            "refresh_token": "test-refresh-token",
            "refresh_token_expires_in": 15_000_000,
            "token_type": "bearer",
        })

    async def get(self, url, *, headers=None, **kwargs):
        assert url == github_auth.GITHUB_USER_URL
        assert headers["Authorization"] == "Bearer test-access-token"
        return FakeResponse({
            "id": 12345,
            "login": "octocat-test",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345?v=4",
        })


def configure_oauth(monkeypatch):
    monkeypatch.setenv("NEXAPATCH_ENV", "development")
    monkeypatch.setenv("GITHUB_APP_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GITHUB_APP_CLIENT_SECRET", "test-client-secret-not-real")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "https://api.example.test/auth/github/callback")
    monkeypatch.setenv("NEXAPATCH_FRONTEND_URL", "https://frontend.example.test")
    monkeypatch.setenv("NEXAPATCH_SESSION_SECRET", "test-only-session-secret-with-more-than-32-characters")


def test_github_oauth_login_callback_me_and_logout(monkeypatch):
    configure_oauth(monkeypatch)
    monkeypatch.setattr(github_auth.httpx, "AsyncClient", FakeAsyncClient)

    with TestClient(agent.app) as client:
        login = client.get("/auth/github/login", follow_redirects=False)
        assert login.status_code == 302
        authorize_url = urlparse(login.headers["location"])
        assert authorize_url.netloc == "github.com"
        query = parse_qs(authorize_url.query)
        assert query["client_id"] == ["test-client-id"]
        assert query["code_challenge_method"] == ["S256"]
        state = query["state"][0]

        callback = client.get(
            f"/auth/github/callback?code=fake-code&state={state}",
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert "github_login=success" in callback.headers["location"]
        cookie_header = callback.headers.get("set-cookie", "")
        assert "HttpOnly" in cookie_header
        assert "test-access-token" not in cookie_header

        me = client.get("/auth/me")
        assert me.status_code == 200
        assert me.json() == {
            "authenticated": True,
            "user": {
                "id": 12345,
                "login": "octocat-test",
                "avatar_url": "https://avatars.githubusercontent.com/u/12345?v=4",
            },
        }
        assert "test-access-token" not in me.text

        logged_out = client.post("/auth/logout")
        assert logged_out.status_code == 200
        assert logged_out.json() == {"logged_out": True}
        assert client.get("/auth/me").json() == {"authenticated": False, "user": None}


def test_github_callback_rejects_invalid_state(monkeypatch):
    configure_oauth(monkeypatch)
    with TestClient(agent.app) as client:
        login = client.get("/auth/github/login", follow_redirects=False)
        assert login.status_code == 302
        callback = client.get(
            "/auth/github/callback?code=fake-code&state=wrong-state",
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert "github_login=error" in callback.headers["location"]
        assert "reason=invalid_state" in callback.headers["location"]
        assert client.get("/auth/me").json() == {"authenticated": False, "user": None}


def test_github_oauth_fails_closed_when_unconfigured(monkeypatch):
    configure_oauth(monkeypatch)
    monkeypatch.delenv("GITHUB_APP_CLIENT_SECRET", raising=False)
    with TestClient(agent.app) as client:
        response = client.get("/auth/github/login")
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]
