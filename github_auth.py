"""GitHub App OAuth endpoints for NexaPatch.

OAuth tokens are kept inside an authenticated, encrypted, HttpOnly cookie; they
are never returned to JavaScript. API routes continue to require the existing
bearer token until user-scoped history and request authorization are implemented.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter(tags=["GitHub authentication"])

SESSION_COOKIE = "nexapatch_session"
STATE_COOKIE = "nexapatch_oauth_state"
PKCE_COOKIE = "nexapatch_pkce_verifier"
SESSION_MAX_AGE = 7 * 24 * 60 * 60
OAUTH_COOKIE_MAX_AGE = 10 * 60
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _configuration() -> dict[str, str]:
    keys = {
        "client_id": "GITHUB_APP_CLIENT_ID",
        "client_secret": "GITHUB_APP_CLIENT_SECRET",
        "redirect_uri": "GITHUB_REDIRECT_URI",
        "frontend_url": "NEXAPATCH_FRONTEND_URL",
        "session_secret": "NEXAPATCH_SESSION_SECRET",
    }
    values = {key: _env(env_name) for key, env_name in keys.items()}
    if any(not value for value in values.values()):
        raise ValueError("GitHub authentication is not fully configured.")
    if len(values["session_secret"]) < 32:
        raise ValueError("The session secret must contain at least 32 characters.")
    if not values["frontend_url"].startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise ValueError("The configured frontend URL is invalid.")
    if not values["redirect_uri"].startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise ValueError("The configured GitHub redirect URI is invalid.")
    values["frontend_url"] = values["frontend_url"].rstrip("/")
    return values


def _fernet() -> Fernet:
    secret = _env("NEXAPATCH_SESSION_SECRET")
    if len(secret) < 32:
        raise ValueError("The session secret must contain at least 32 characters.")
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(derived_key)


def _secure_cookie() -> bool:
    return _env("NEXAPATCH_ENV").lower() in {"production", "prod"}


def _session_samesite() -> str:
    # Separate hosted frontend/API hostnames may require cross-site cookies.
    return "none" if _secure_cookie() else "lax"


def _frontend_redirect(*, success: bool, reason: str = "") -> RedirectResponse:
    frontend = _env("NEXAPATCH_FRONTEND_URL") or "http://localhost:5173"
    query = {"github_login": "success" if success else "error"}
    if reason:
        # Fixed internal reason codes only; never reflect arbitrary query values.
        query["reason"] = reason
    return RedirectResponse(f"{frontend.rstrip('/')}/?{urlencode(query)}", status_code=303)


def _set_temp_cookie(response: RedirectResponse, name: str, value: str) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=OAUTH_COOKIE_MAX_AGE,
        path="/auth/github/callback",
        secure=_secure_cookie(),
        httponly=True,
        samesite="lax",
    )


def _clear_oauth_cookies(response: RedirectResponse) -> None:
    for name in (STATE_COOKIE, PKCE_COOKIE):
        response.delete_cookie(
            key=name,
            path="/auth/github/callback",
            secure=_secure_cookie(),
            httponly=True,
            samesite="lax",
        )


def _write_session_cookie(response: JSONResponse | RedirectResponse, payload: dict[str, Any]) -> None:
    encrypted = _fernet().encrypt(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
    if len(encrypted) > 3500:
        raise ValueError("The encrypted session exceeds the safe cookie size limit.")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=encrypted,
        max_age=SESSION_MAX_AGE,
        path="/",
        secure=_secure_cookie(),
        httponly=True,
        samesite=_session_samesite(),
    )


def _read_session(request: Request) -> dict[str, Any] | None:
    encoded = request.cookies.get(SESSION_COOKIE)
    if not encoded:
        return None
    try:
        payload = json.loads(_fernet().decrypt(encoded.encode("ascii"), ttl=SESSION_MAX_AGE))
    except (InvalidToken, ValueError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("version") != 1:
        return None
    user = payload.get("user")
    if not isinstance(user, dict) or not isinstance(user.get("id"), int) or not isinstance(user.get("login"), str):
        return None
    if not isinstance(payload.get("access_token"), str) or not payload.get("access_token"):
        return None
    return payload


def get_session_identity(request: Request) -> dict[str, Any] | None:
    """Return a token-free identity from a valid encrypted GitHub session."""
    payload = _read_session(request)
    if payload is None:
        return None
    user = payload["user"]
    return {"user_id": str(user["id"]), "login": user["login"]}


GUEST_COOKIE = "nexapatch_guest"
GUEST_COOKIE_MAX_AGE = 30 * 24 * 60 * 60


def _guest_signing_key() -> bytes:
    """Derive a purpose-specific key without exposing it to browser JavaScript."""
    secret = _env("NEXAPATCH_SESSION_SECRET")
    if len(secret) < 32:
        if _secure_cookie():
            raise ValueError("A session secret of at least 32 characters is required for guest cookies.")
        secret = "local-development-only-nexapatch-guest-cookie-secret"
    return hashlib.sha256(("nexapatch-guest-cookie-v1:" + secret).encode("utf-8")).digest()


def _guest_cookie_signature(guest_id: str, issued_at: int) -> str:
    message = f"{guest_id}.{issued_at}".encode("ascii")
    signature = hmac.new(_guest_signing_key(), message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


def _read_guest_identity(request: Request) -> str | None:
    value = request.cookies.get(GUEST_COOKIE, "")
    try:
        guest_id, raw_issued_at, supplied_signature = value.split(".", 2)
        issued_at = int(raw_issued_at)
        now = int(time.time())
        if not guest_id or issued_at > now + 300 or issued_at < now - GUEST_COOKIE_MAX_AGE:
            return None
        expected_signature = _guest_cookie_signature(guest_id, issued_at)
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None
        return guest_id
    except (ValueError, UnicodeError):
        return None


def _write_guest_cookie(response: Response, guest_id: str) -> None:
    issued_at = int(time.time())
    value = f"{guest_id}.{issued_at}.{_guest_cookie_signature(guest_id, issued_at)}"
    response.set_cookie(
        key=GUEST_COOKIE,
        value=value,
        max_age=GUEST_COOKIE_MAX_AGE,
        path="/",
        secure=_secure_cookie(),
        httponly=True,
        samesite=_session_samesite(),
    )


def get_or_create_guest_identity(request: Request, response: Response) -> str:
    """Return the verified guest ID, creating a signed browser cookie if needed."""
    existing = _read_guest_identity(request)
    if existing is not None:
        return existing
    guest_id = secrets.token_urlsafe(24)
    _write_guest_cookie(response, guest_id)
    return guest_id


def _delete_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=_secure_cookie(),
        httponly=True,
        samesite=_session_samesite(),
    )


def _unauthenticated_response(*, clear_cookie: bool = False) -> JSONResponse:
    response = JSONResponse({"authenticated": False, "user": None})
    if clear_cookie:
        _delete_session_cookie(response)
    return response


async def _refresh_session(payload: dict[str, Any], config: dict[str, str]) -> dict[str, Any] | None:
    refresh_token = payload.get("refresh_token")
    refresh_expiry = payload.get("refresh_token_expires_at")
    now = int(time.time())
    if not isinstance(refresh_token, str) or not refresh_token:
        return None
    if isinstance(refresh_expiry, (int, float)) and refresh_expiry <= now + 60:
        return None
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json", "User-Agent": "NexaPatch"},
                data={
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
        if response.status_code != 200:
            return None
        tokens = response.json()
        if not isinstance(tokens, dict) or not isinstance(tokens.get("access_token"), str):
            return None
        updated = dict(payload)
        updated["access_token"] = tokens["access_token"]
        expires_in = tokens.get("expires_in")
        updated["access_token_expires_at"] = now + int(expires_in) if isinstance(expires_in, (int, float)) else None
        rotated_refresh = tokens.get("refresh_token")
        if isinstance(rotated_refresh, str) and rotated_refresh:
            updated["refresh_token"] = rotated_refresh
        refresh_expires_in = tokens.get("refresh_token_expires_in")
        if isinstance(refresh_expires_in, (int, float)):
            updated["refresh_token_expires_at"] = now + int(refresh_expires_in)
        return updated
    except (httpx.HTTPError, ValueError, TypeError):
        return None


@router.get("/auth/github/login")
async def github_login() -> RedirectResponse:
    """Begin GitHub App OAuth authorization with state and PKCE."""
    try:
        config = _configuration()
        _fernet()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="GitHub authentication is not configured.") from exc

    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    response = RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}", status_code=302)
    _set_temp_cookie(response, STATE_COOKIE, state)
    _set_temp_cookie(response, PKCE_COOKIE, verifier)
    return response


@router.get("/auth/github/callback")
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Validate OAuth state, exchange the code, fetch the user, and create a session."""
    if error:
        response = _frontend_redirect(success=False, reason="authorization_denied")
        _clear_oauth_cookies(response)
        return response

    state_cookie = request.cookies.get(STATE_COOKIE, "")
    verifier = request.cookies.get(PKCE_COOKIE, "")
    if not code or not state or not state_cookie or not verifier or not hmac.compare_digest(state, state_cookie):
        response = _frontend_redirect(success=False, reason="invalid_state")
        _clear_oauth_cookies(response)
        return response

    try:
        config = _configuration()
        _fernet()
    except ValueError:
        response = _frontend_redirect(success=False, reason="auth_not_configured")
        _clear_oauth_cookies(response)
        return response

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
            token_response = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json", "User-Agent": "NexaPatch"},
                data={
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "code": code,
                    "redirect_uri": config["redirect_uri"],
                    "code_verifier": verifier,
                },
            )
            if token_response.status_code != 200:
                response = _frontend_redirect(success=False, reason="token_exchange_failed")
                _clear_oauth_cookies(response)
                return response
            tokens = token_response.json()
            access_token = tokens.get("access_token") if isinstance(tokens, dict) else None
            if not isinstance(access_token, str) or not access_token:
                response = _frontend_redirect(success=False, reason="token_exchange_failed")
                _clear_oauth_cookies(response)
                return response

            user_response = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "NexaPatch",
                },
            )
            if user_response.status_code != 200:
                response = _frontend_redirect(success=False, reason="profile_fetch_failed")
                _clear_oauth_cookies(response)
                return response
            profile = user_response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        response = _frontend_redirect(success=False, reason="github_request_failed")
        _clear_oauth_cookies(response)
        return response

    if (
        not isinstance(profile, dict)
        or not isinstance(profile.get("id"), int)
        or not isinstance(profile.get("login"), str)
        or not profile["login"].strip()
    ):
        response = _frontend_redirect(success=False, reason="profile_invalid")
        _clear_oauth_cookies(response)
        return response

    now = int(time.time())
    expires_in = tokens.get("expires_in")
    refresh_expires_in = tokens.get("refresh_token_expires_in")
    refresh_token = tokens.get("refresh_token")
    session = {
        "version": 1,
        "issued_at": now,
        "user": {
            "id": profile["id"],
            "login": profile["login"].strip(),
            "avatar_url": profile.get("avatar_url") if isinstance(profile.get("avatar_url"), str) else "",
        },
        "access_token": access_token,
        "access_token_expires_at": now + int(expires_in) if isinstance(expires_in, (int, float)) else None,
        "refresh_token": refresh_token if isinstance(refresh_token, str) and refresh_token else None,
        "refresh_token_expires_at": now + int(refresh_expires_in) if isinstance(refresh_expires_in, (int, float)) else None,
    }
    try:
        response = _frontend_redirect(success=True)
        _write_session_cookie(response, session)
    except (ValueError, TypeError):
        response = _frontend_redirect(success=False, reason="session_creation_failed")
    _clear_oauth_cookies(response)
    return response


@router.get("/auth/me")
async def auth_me(request: Request) -> JSONResponse:
    """Return the current authenticated GitHub identity, never OAuth tokens."""
    payload = _read_session(request)
    if payload is None:
        response = _unauthenticated_response(clear_cookie=bool(request.cookies.get(SESSION_COOKIE)))
        # Guest access is opt-in so a missing environment variable never silently opens the API.
        guests_enabled = _env("NEXAPATCH_GUEST_ACCESS_ENABLED").lower() in {"1", "true", "yes", "on"}
        if guests_enabled:
            get_or_create_guest_identity(request, response)
        return response

    expires_at = payload.get("access_token_expires_at")
    now = int(time.time())
    updated_session = False
    if isinstance(expires_at, (int, float)) and expires_at <= now + 60:
        try:
            config = _configuration()
            refreshed = await _refresh_session(payload, config)
        except ValueError:
            refreshed = None
        if refreshed is None:
            return _unauthenticated_response(clear_cookie=True)
        payload = refreshed
        updated_session = True

    user = payload["user"]
    response = JSONResponse({
        "authenticated": True,
        "user": {
            "id": user["id"],
            "login": user["login"],
            "avatar_url": user.get("avatar_url", ""),
        },
    })
    if updated_session:
        try:
            _write_session_cookie(response, payload)
        except (ValueError, TypeError):
            return _unauthenticated_response(clear_cookie=True)
    return response


@router.post("/auth/logout")
async def github_logout() -> JSONResponse:
    """Clear the browser's encrypted session cookie."""
    response = JSONResponse({"logged_out": True})
    _delete_session_cookie(response)
    return response
