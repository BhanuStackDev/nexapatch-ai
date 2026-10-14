"""Bounded, read-only downloader for public GitHub repositories.

Only canonical https://github.com/{owner}/{repo} URLs are accepted. The module
never runs repository code, never follows archive links from repository files,
and only writes inspectable regular text files to a caller-owned temporary dir.
"""
from __future__ import annotations

import io
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit

import httpx

from repository_scanner import _is_text_candidate

API_ROOT = "https://api.github.com"
USER_AGENT = "NexaPatch-ReadOnly-Repository-Inspector"
MAX_ARCHIVE_BYTES = 12 * 1024 * 1024
MAX_EXPANDED_BYTES = 20 * 1024 * 1024
MAX_FILE_BYTES = 1024 * 1024
MAX_EXTRACTED_FILES = 600
MAX_ARCHIVE_ENTRIES = 5_000
# Bound declared uncompressed content across ALL regular files, including ignored binaries.
MAX_DECLARED_FILE_BYTES = 64 * 1024 * 1024
_ALLOWED_ARCHIVE_HOSTS = {"api.github.com", "github.com", "codeload.github.com"}
_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


class PublicRepositoryError(Exception):
    """A safe, client-displayable repository retrieval error."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class MaterializedPublicRepository:
    owner: str
    name: str
    full_name: str
    url: str
    root: Path
    files_written: int


def parse_public_github_url(value: str) -> tuple[str, str, str]:
    """Accept only an HTTPS GitHub repository root URL."""
    if not isinstance(value, str) or not value or len(value) > 2_048:
        raise PublicRepositoryError(400, "Enter a valid public GitHub repository URL.")
    try:
        parsed = urlsplit(value.strip())
    except ValueError as exc:
        raise PublicRepositoryError(400, "Enter a valid public GitHub repository URL.") from exc
    if (
        parsed.scheme.lower() != "https"
        or parsed.netloc.lower() != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "%" in parsed.path
        or "\\" in parsed.path
    ):
        raise PublicRepositoryError(400, "Use a canonical https://github.com/owner/repository URL.")

    path = parsed.path.strip("/")
    parts = path.split("/") if path else []
    if len(parts) != 2:
        raise PublicRepositoryError(400, "Enter a repository root URL, not a branch, file, or pull-request URL.")
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not _OWNER_RE.fullmatch(owner) or not _REPO_RE.fullmatch(repo) or repo in {".", ".."}:
        raise PublicRepositoryError(400, "The GitHub owner or repository name is invalid.")
    canonical_url = f"https://github.com/{owner}/{repo}"
    return owner, repo, canonical_url


def _safe_extract_tarball(payload: bytes, destination: Path) -> int:
    """Extract eligible regular text files while rejecting traversal and size bombs."""
    root = destination.resolve()
    root.mkdir(parents=True, exist_ok=True)
    files_written = 0
    expanded_bytes = 0
    declared_file_bytes = 0
    entries_seen = 0
    archive_root: str | None = None

    try:
        archive_context = tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz")
    except (tarfile.TarError, OSError) as exc:
        raise PublicRepositoryError(502, "GitHub returned an unreadable repository archive.") from exc

    with archive_context as archive:
        try:
            for member in archive:
                entries_seen += 1
                if entries_seen > MAX_ARCHIVE_ENTRIES:
                    raise PublicRepositoryError(413, "The repository archive has too many entries.")

                raw_name = member.name
                # Enforce a total expanded-content limit even for binary/ignored files.
                # Otherwise a small gzip archive could declare huge ignored members.
                if member.isfile():
                    if member.size < 0:
                        raise PublicRepositoryError(400, "The repository archive contains an invalid file size.")
                    declared_file_bytes += member.size
                    if declared_file_bytes > MAX_DECLARED_FILE_BYTES:
                        raise PublicRepositoryError(413, "The repository archive declares too much file content to inspect safely.")
                if not raw_name or raw_name.startswith("/") or "\\" in raw_name:
                    raise PublicRepositoryError(400, "The repository archive contains an unsafe path.")
                normalized_name = raw_name.rstrip("/")
                parts = normalized_name.split("/")
                if not normalized_name or any(part in {"", ".", ".."} for part in parts):
                    raise PublicRepositoryError(400, "The repository archive contains an unsafe path.")
                if archive_root is None:
                    archive_root = parts[0]
                if parts[0] != archive_root:
                    raise PublicRepositoryError(400, "The repository archive has an unexpected directory layout.")
                relative_parts = parts[1:]
                if not relative_parts:
                    continue

                # Do not materialize hidden trees such as .git/.github. This also
                # mirrors the scanner's policy of omitting hidden directories.
                if any(part.startswith(".") for part in relative_parts[:-1]):
                    continue
                if not member.isfile():
                    # Symlinks, hardlinks, devices, and other special entries are
                    # never extracted; an archive cannot create filesystem links.
                    continue
                if member.size < 0 or member.size > MAX_FILE_BYTES:
                    continue
                relative_path = PurePosixPath(*relative_parts)
                target = root.joinpath(*relative_parts)
                try:
                    target_resolved = target.resolve(strict=False)
                    target_resolved.relative_to(root)
                except (OSError, ValueError):
                    raise PublicRepositoryError(400, "The repository archive contains an unsafe path.")

                if not _is_text_candidate(target):
                    continue
                if files_written >= MAX_EXTRACTED_FILES:
                    raise PublicRepositoryError(413, "The repository has too many source files for one analysis.")
                if expanded_bytes + member.size > MAX_EXPANDED_BYTES:
                    raise PublicRepositoryError(413, "The repository source files exceed the analysis size limit.")

                source = archive.extractfile(member)
                if source is None:
                    continue
                with source:
                    content = source.read(MAX_FILE_BYTES + 1)
                if len(content) != member.size or len(content) > MAX_FILE_BYTES:
                    raise PublicRepositoryError(413, "A source file exceeds the allowed size limit.")

                target.parent.mkdir(parents=True, exist_ok=True)
                # Check the destination after parent creation, before writing.
                try:
                    target.resolve(strict=False).relative_to(root)
                except (OSError, ValueError):
                    raise PublicRepositoryError(400, "The repository archive contains an unsafe path.")
                target.write_bytes(content)
                files_written += 1
                expanded_bytes += len(content)
        except PublicRepositoryError:
            raise
        except (tarfile.TarError, OSError, EOFError) as exc:
            raise PublicRepositoryError(502, "GitHub returned an incomplete repository archive.") from exc

    if files_written == 0:
        raise PublicRepositoryError(422, "No eligible text/source files were found in this public repository.")
    return files_written


def _http_error(response: httpx.Response, operation: str) -> PublicRepositoryError:
    if response.status_code == 404:
        return PublicRepositoryError(404, "Public GitHub repository was not found.")
    if response.status_code in {403, 429}:
        return PublicRepositoryError(429, "GitHub is rate-limiting repository downloads. Try again later.")
    return PublicRepositoryError(502, f"GitHub could not {operation} (HTTP {response.status_code}).")


REDIRECT_STATUSES = {301, 302, 303, 307, 308}
MAX_REDIRECT_HOPS = 3


def _validate_redirect_target(value: str, allowed_hosts: set[str]) -> None:
    """Reject unsafe redirect destinations before making a request to them."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
        hostname = (parsed.hostname or "").lower()
    except ValueError as exc:
        raise PublicRepositoryError(502, "GitHub redirect target was rejected.") from exc
    if (
        parsed.scheme.lower() != "https"
        or hostname not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise PublicRepositoryError(502, "GitHub redirect target was rejected.")


async def _send_with_safe_redirects(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    allowed_hosts: set[str],
    stream: bool,
) -> httpx.Response:
    """Follow a small number of HTTPS redirects, validating every hop first."""
    current_url = url
    for hop in range(MAX_REDIRECT_HOPS + 1):
        _validate_redirect_target(current_url, allowed_hosts)
        request = client.build_request(method, current_url, headers=headers)
        response = await client.send(request, stream=stream, follow_redirects=False)
        if response.status_code not in REDIRECT_STATUSES:
            return response

        if hop >= MAX_REDIRECT_HOPS:
            await response.aclose()
            raise PublicRepositoryError(502, "GitHub returned too many redirects.")
        location = response.headers.get("location")
        if not location:
            await response.aclose()
            raise PublicRepositoryError(502, "GitHub returned a redirect without a destination.")
        try:
            next_url = str(response.url.join(location))
            _validate_redirect_target(next_url, allowed_hosts)
        except PublicRepositoryError:
            await response.aclose()
            raise
        except ValueError as exc:
            await response.aclose()
            raise PublicRepositoryError(502, "GitHub redirect target was rejected.") from exc
        await response.aclose()
        current_url = next_url

    raise PublicRepositoryError(502, "GitHub returned too many redirects.")


async def materialize_public_github_repository(
    repository_url: str,
    destination: Path,
) -> MaterializedPublicRepository:
    """Download an anonymous public GitHub archive into a safe temporary directory."""
    owner, name, canonical_url = parse_public_github_url(repository_url)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    timeout = httpx.Timeout(15.0, connect=8.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, max_redirects=3) as client:
            metadata_response = await _send_with_safe_redirects(
                client,
                "GET",
                f"{API_ROOT}/repos/{owner}/{name}",
                headers=headers,
                allowed_hosts={"api.github.com"},
                stream=False,
            )
            if metadata_response.url.host != "api.github.com":
                raise PublicRepositoryError(502, "GitHub metadata redirect was rejected.")
            if metadata_response.status_code != 200:
                raise _http_error(metadata_response, "read repository metadata")
            metadata = metadata_response.json()
            if not isinstance(metadata, dict):
                raise PublicRepositoryError(502, "GitHub returned invalid repository metadata.")
            if metadata.get("private") is True:
                raise PublicRepositoryError(403, "Only public GitHub repositories can be analyzed by this endpoint.")
            default_branch = metadata.get("default_branch")
            if not isinstance(default_branch, str) or not default_branch or len(default_branch) > 255:
                raise PublicRepositoryError(422, "GitHub did not provide a valid default branch.")

            archive_url = f"{API_ROOT}/repos/{owner}/{name}/tarball/{quote(default_branch, safe='')}"
            payload = bytearray()
            response = await _send_with_safe_redirects(
                client,
                "GET",
                archive_url,
                headers=headers,
                allowed_hosts=_ALLOWED_ARCHIVE_HOSTS,
                stream=True,
            )
            try:
                if response.status_code != 200:
                    raise _http_error(response, "download the repository archive")
                content_length = response.headers.get("content-length")
                if content_length and content_length.isdigit() and int(content_length) > MAX_ARCHIVE_BYTES:
                    raise PublicRepositoryError(413, "The compressed repository archive exceeds 12 MiB.")
                async for chunk in response.aiter_bytes():
                    if len(payload) + len(chunk) > MAX_ARCHIVE_BYTES:
                        raise PublicRepositoryError(413, "The compressed repository archive exceeds 12 MiB.")
                    payload.extend(chunk)
            finally:
                await response.aclose()
    except PublicRepositoryError:
        raise
    except httpx.TooManyRedirects as exc:
        raise PublicRepositoryError(502, "GitHub returned too many redirects.") from exc
    except httpx.TimeoutException as exc:
        raise PublicRepositoryError(504, "GitHub repository download timed out. Please retry.") from exc
    except httpx.HTTPError as exc:
        raise PublicRepositoryError(502, "GitHub repository download failed. Please retry.") from exc
    except (ValueError, TypeError) as exc:
        raise PublicRepositoryError(502, "GitHub returned invalid repository metadata.") from exc

    files_written = _safe_extract_tarball(bytes(payload), destination)
    return MaterializedPublicRepository(
        owner=owner,
        name=name,
        full_name=f"{owner}/{name}",
        url=canonical_url,
        root=destination.resolve(),
        files_written=files_written,
    )
