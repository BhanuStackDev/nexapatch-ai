"""Read-only repository inspection helpers for ConversAI.

This module deliberately does not import AI/backend dependencies, so the scanner
can be tested independently and safely. It never reads common secret files.
"""
from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path
from typing import Any
from secret_redaction import redact_secrets

IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "dist", "build", ".next", "coverage", ".pytest_cache", "__pycache__",
    ".mypy_cache", ".ruff_cache", ".cache", ".idea", ".vscode", "vendor",
    "target", "uploads", "site-packages",
}
IGNORED_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".log", ".pyc", ".pyo", ".class",
    ".jar", ".war", ".zip", ".7z", ".rar", ".pdf", ".png", ".jpg",
    ".jpeg", ".gif", ".webp", ".ico", ".mp4", ".mov", ".mp3", ".wav",
    ".woff", ".woff2", ".ttf", ".otf", ".exe", ".dll", ".so", ".dylib",
    ".pem", ".p12", ".pfx", ".key", ".crt", ".cer",
}
TEXT_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".json", ".md", ".mdx", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".html", ".htm", ".css", ".scss", ".sass", ".sql", ".sh", ".bat",
    ".ps1", ".kt", ".java", ".go", ".rs", ".php", ".rb", ".dart",
    ".swift", ".xml", ".properties", ".gradle", ".dockerfile", ".txt",
}
# Explicit project code and entry points must outrank documentation so the model
# receives implementation evidence before it drafts a plan.
CORE_FILE_PRIORITIES = {
    "agent.py": 260,
    "repository_scanner.py": 250,
    "frontend/src/main.jsx": 245,
    "frontend/src/main.tsx": 245,
    "frontend/src/app.jsx": 240,
    "frontend/src/app.tsx": 240,
    "frontend/src/app.ts": 240,
    "frontend/src/app.js": 240,
    "frontend/package.json": 225,
    "requirements.txt": 225,
    "tests/test_repository_scanner.py": 215,
    "pyproject.toml": 210,
    "package.json": 205,
    "main.py": 200,
    "app.py": 195,
    "server.py": 190,
}
IMPORTANT_FILES = {
    # Documentation remains useful, but should not crowd out executable source.
    "readme.md": 45, "readme": 45, "pyproject.toml": 95,
    "requirements.txt": 95, "package.json": 95, "dockerfile": 90,
    "docker-compose.yml": 90, "docker-compose.yaml": 90,
    "compose.yml": 90, "compose.yaml": 90, "vite.config.js": 80,
    "vite.config.ts": 80, "tsconfig.json": 75, "pytest.ini": 75,
}
SECRET_NAME_MARKERS = ("secret", "credential", "private_key", "id_rsa", "token_store")
TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]{2,}")
STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your",
    "please", "make", "build", "add", "fix", "change", "code", "file",
    "files", "application", "project", "existing", "current", "should",
    "would", "could", "have", "will", "then", "when", "where", "what",
}


def is_sensitive_or_generated(path: Path) -> bool:
    name = path.name.lower()
    if name == ".env" or name.startswith(".env."):
        return True
    if name in {"credentials.json", "secrets.json", "service-account.json"}:
        return True
    if any(marker in name for marker in SECRET_NAME_MARKERS):
        return True
    if path.suffix.lower() in IGNORED_SUFFIXES:
        return True
    if name.endswith((".pem", ".key", ".p12", ".pfx", ".crt", ".cer")):
        return True
    return False


def _is_text_candidate(path: Path) -> bool:
    name = path.name.lower()
    if is_sensitive_or_generated(path):
        return False
    if name in {"dockerfile", "makefile", "justfile", "procfile"}:
        return True
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    # Avoid arbitrary extensionless logs, executables and binary-looking files.
    return True


def _score_file(relative: str, prompt_tokens: set[str]) -> int:
    path = Path(relative)
    name = path.name.lower()
    score = max(
        IMPORTANT_FILES.get(name, 0),
        CORE_FILE_PRIORITIES.get(relative.lower(), 0),
        CORE_FILE_PRIORITIES.get(name, 0),
    )
    parts = {part.lower() for part in re.split(r"[/_.\\-]+", relative) if len(part) > 2}
    score += 12 * len(parts & prompt_tokens)
    if path.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".jsx"}:
        score += 12
    if any(part in {"test", "tests", "spec", "specs"} for part in parts):
        score += 8
    return score


def scan_repository(
    root: str | Path,
    request_text: str,
    *,
    max_discovered_files: int = 600,
    max_context_files: int = 8,
    max_file_chars: int = 2_200,
    max_context_chars: int = 12_000,
) -> dict[str, Any]:
    """Return a bounded, read-only inventory and selected source context.

    It skips generated/dependency directories, symlinks and common secret files.
    It does not execute code, invoke Git, or mutate the workspace.
    """
    repo_root = Path(root).expanduser().resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise ValueError("TARGET_REPO_PATH must point to an existing directory.")

    paths: list[Path] = []
    total_candidates = 0
    truncated_inventory = False
    for current, dirnames, filenames in os.walk(repo_root, topdown=True, followlinks=False):
        current_path = Path(current)
        dirnames[:] = sorted(
            name for name in dirnames
            if name not in IGNORED_DIRS
            and not name.startswith(".")
            and not (current_path / name).is_symlink()
        )
        for filename in sorted(filenames):
            # Ignore local temporary patch/helper scripts stored in the repository root.
            # Keep the rule root-only so application modules in subfolders are still scanned.
            if (
                current_path == repo_root
                and filename.lower().startswith("nexapatch_")
                and filename.lower().endswith(".py")
            ):
                continue

            candidate = current_path / filename
            if candidate.is_symlink() or not _is_text_candidate(candidate):
                continue
            try:
                relative = candidate.relative_to(repo_root).as_posix()
            except ValueError:
                continue
            total_candidates += 1
            if len(paths) < max_discovered_files:
                paths.append(candidate)
            else:
                truncated_inventory = True
                break
        if truncated_inventory:
            break

    if not paths:
        raise ValueError("No inspectable text/source files were found in the configured workspace.")

    prompt_tokens = {
        token.lower() for token in TOKEN_RE.findall(request_text)
        if token.lower() not in STOP_WORDS
    }
    relative_paths = [p.relative_to(repo_root).as_posix() for p in paths]
    ranked = sorted(
        zip(paths, relative_paths),
        key=lambda item: (_score_file(item[1], prompt_tokens), item[1].count("/")),
        reverse=True,
    )

    # Select from one ranking so core implementation files reliably outrank
    # README files. Pinning many documentation files used to crowd out agent.py.
    selected: list[tuple[Path, str]] = []
    selected_paths: set[str] = set()
    for item in ranked:
        if len(selected) >= max_context_files:
            break
        if item[1] not in selected_paths:
            selected.append(item)
            selected_paths.add(item[1])

    context_blocks: list[str] = []
    context_chars = 0
    files_in_context: list[str] = []
    for path, relative in selected:
        try:
            raw = path.read_bytes()
            if b"\x00" in raw[:4_096]:
                continue
            content = raw.decode("utf-8", errors="replace")
            content = redact_secrets(content)
            if len(content) > max_file_chars:
                # Preserve both imports/configuration and routes/classes at the end
                # of long files rather than silently sending only the first lines.
                head_chars = max_file_chars // 2
                tail_chars = max_file_chars - head_chars
                omitted_chars = len(content) - max_file_chars
                content = (
                    content[:head_chars]
                    + f"\n\n...[middle omitted: {omitted_chars} characters; inspect locally for full file]...\n\n"
                    + content[-tail_chars:]
                )
        except (OSError, PermissionError):
            continue
        if not content.strip():
            continue
        block = f"\n--- FILE: {relative} ---\n{content}\n"
        if context_chars + len(block) > max_context_chars:
            break
        context_blocks.append(block)
        files_in_context.append(relative)
        context_chars += len(block)

    language_counts = Counter(
        p.suffix.lower().lstrip(".") or "extensionless"
        for p in paths
    )
    project_name = repo_root.name or str(repo_root)
    lang_summary = ", ".join(
        f"{ext} ({count})" for ext, count in language_counts.most_common(6)
    )
    summary = (
        f"Workspace: {project_name}. Inspectable files found: {len(paths)}"
        + (f" (inventory capped at {max_discovered_files})." if truncated_inventory else ".")
        + f" Dominant file types: {lang_summary or 'not detected'}. "
        + f"Selected {len(files_in_context)} files for AI context. "
        + "This is a read-only scan; no project files were changed or executed."
    )
    return {
        "workspace_name": project_name,
        "repository_root": str(repo_root),
        "discovered_files": relative_paths,
        "files_in_context": files_in_context,
        "source_context": "\n".join(context_blocks),
        "repository_summary": summary,
        "total_files_found": len(paths),
        "inventory_truncated": truncated_inventory,
    }
