"""Offline tests for safe public GitHub repository intake."""
from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import github_repository as github_repository_module
import agent as agent_module
from github_repository import (
    PublicRepositoryError,
    _send_with_safe_redirects,
    _safe_extract_tarball,
    materialize_public_github_repository,
    parse_public_github_url,
)


def _tarball(entries: list[tuple[str, bytes, bytes | None]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content, entry_type in entries:
            info = tarfile.TarInfo(name)
            info.type = entry_type or tarfile.REGTYPE
            info.size = len(content) if info.type == tarfile.REGTYPE else 0
            if info.type == tarfile.REGTYPE:
                archive.addfile(info, io.BytesIO(content))
            else:
                if info.type == tarfile.SYMTYPE:
                    info.linkname = "../../outside.py"
                archive.addfile(info)
    return buffer.getvalue()


def test_parse_public_repository_root_urls() -> None:
    assert parse_public_github_url("https://github.com/octo-org/sample-repo/") == (
        "octo-org", "sample-repo", "https://github.com/octo-org/sample-repo"
    )
    assert parse_public_github_url("https://github.com/octo-org/sample-repo.git") == (
        "octo-org", "sample-repo", "https://github.com/octo-org/sample-repo"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/octo-org/repo",
        "https://github.com.evil.example/octo-org/repo",
        "https://user@github.com/octo-org/repo",
        "https://github.com/octo-org/repo/tree/main",
        "https://github.com/octo-org/repo?download=1",
        "https://github.com/octo-org/%2e%2e",
    ],
)
def test_parse_rejects_noncanonical_or_unsafe_urls(url: str) -> None:
    with pytest.raises(PublicRepositoryError):
        parse_public_github_url(url)


def test_safe_extractor_writes_only_eligible_regular_source_files(tmp_path: Path) -> None:
    payload = _tarball([
        ("octo-repo-main/", b"", tarfile.DIRTYPE),
        ("octo-repo-main/main.py", b"print('safe')\n", None),
        ("octo-repo-main/.env", b"SHOULD_NOT_BE_WRITTEN=x", None),
        ("octo-repo-main/config-secret.txt", b"SHOULD_NOT_BE_WRITTEN=x", None),
        ("octo-repo-main/link.py", b"", tarfile.SYMTYPE),
        ("octo-repo-main/.git/config", b"not needed", None),
    ])
    written = _safe_extract_tarball(payload, tmp_path)
    assert written == 1
    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "print('safe')\n"
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / "config-secret.txt").exists()
    assert not (tmp_path / "link.py").exists()
    assert not (tmp_path / ".git").exists()


def test_safe_extractor_bounds_declared_size_of_ignored_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The file is binary/ignored by the scanner, but its declared bytes still count.
    monkeypatch.setattr(github_repository_module, "MAX_DECLARED_FILE_BYTES", 5)
    payload = _tarball([
        ("octo-repo-main/large.bin", b"123456", None),
    ])
    with pytest.raises(PublicRepositoryError, match="too much file content"):
        _safe_extract_tarball(payload, tmp_path)


def test_safe_extractor_rejects_path_traversal(tmp_path: Path) -> None:
    payload = _tarball([
        ("octo-repo-main/../../outside.py", b"bad", None),
    ])
    with pytest.raises(PublicRepositoryError, match="unsafe path"):
        _safe_extract_tarball(payload, tmp_path)
    assert not (tmp_path.parent / "outside.py").exists()


def test_run_agent_can_scan_public_repository_with_mocked_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakeGraph:
        async def ainvoke(self, state: dict[str, object]) -> dict[str, object]:
            assert Path(str(state["repo_root"])).is_dir()
            return {
                "request_text": state["request_text"],
                "repo_root": state["repo_root"],
                "ai_used": True,
                "ai_error": "",
                "model": "test-model",
                "repository_summary": "Public sample repository.",
                "total_files_found": 1,
                "inventory_truncated": False,
                "discovered_files": ["main.py"],
                "files_in_context": ["main.py"],
                "execution_plan": "1. Inspect safely.",
                "steps": ["Repository inspected"],
            }

    async def fake_materialize(url: str, destination: Path):
        assert url == "https://github.com/octo-org/sample-repo"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "main.py").write_text("print('hello')\n", encoding="utf-8")
        from github_repository import MaterializedPublicRepository
        return MaterializedPublicRepository(
            owner="octo-org",
            name="sample-repo",
            full_name="octo-org/sample-repo",
            url=url,
            root=destination,
            files_written=1,
        )

    monkeypatch.setattr(agent_module, "DB_PATH", tmp_path / "runs.db")
    monkeypatch.setattr(agent_module, "TARGET_REPO_PATH", tmp_path)
    monkeypatch.setattr(agent_module, "agent_graph", FakeGraph())
    monkeypatch.setattr(agent_module, "materialize_public_github_repository", fake_materialize)
    monkeypatch.setattr(agent_module, "NEXAPATCH_API_TOKEN", "")
    monkeypatch.setattr(agent_module, "NEXAPATCH_ENV", "development")

    with TestClient(agent_module.app) as client:
        response = client.post(
            "/api/run-agent",
            json={
                "request_text": "Inspect the public repository safely.",
                "repository_url": "https://github.com/octo-org/sample-repo",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["workspace_name"] == "octo-org/sample-repo"
        history = client.get("/api/runs").json()["runs"]
        assert len(history) == 1
        assert history[0]["workspace_name"] == "octo-org/sample-repo"


def test_repository_url_is_parsed_without_network_access() -> None:
    # URL validation is local; no network calls are made by this test.
    owner, name, canonical = parse_public_github_url("https://github.com/octo-org/private-repo")
    assert (owner, name, canonical) == (
        "octo-org", "private-repo", "https://github.com/octo-org/private-repo"
    )



def test_unsafe_redirect_is_rejected_before_contacting_destination() -> None:
    import asyncio
    import httpx

    contacted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        contacted.append(str(request.url))
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1:8000/internal"},
            request=request,
        )

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(PublicRepositoryError, match="redirect target was rejected"):
                await _send_with_safe_redirects(
                    client,
                    "GET",
                    "https://api.github.com/repos/octo-org/sample-repo",
                    headers={},
                    allowed_hosts={"api.github.com"},
                    stream=False,
                )

    asyncio.run(scenario())
    assert contacted == ["https://api.github.com/repos/octo-org/sample-repo"]


def test_allowed_github_archive_redirect_is_followed() -> None:
    import asyncio
    import httpx

    contacted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        contacted.append(request.url.host or "")
        if request.url.host == "api.github.com":
            return httpx.Response(
                302,
                headers={"Location": "https://codeload.github.com/octo-org/sample-repo/legacy.tar.gz/main"},
                request=request,
            )
        return httpx.Response(200, content=b"archive", request=request)

    async def scenario() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            response = await _send_with_safe_redirects(
                client,
                "GET",
                "https://api.github.com/repos/octo-org/sample-repo/tarball/main",
                headers={},
                allowed_hosts={"api.github.com", "codeload.github.com", "github.com"},
                stream=False,
            )
            try:
                assert response.status_code == 200
                return response.url.host or ""
            finally:
                await response.aclose()

    final_host = asyncio.run(scenario())
    assert final_host == "codeload.github.com"
    assert contacted == ["api.github.com", "codeload.github.com"]
