from pathlib import Path

from repository_scanner import scan_repository


def test_scanner_skips_generated_and_hidden_directories(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        'print("VISIBLE_SOURCE_MARKER")\n', encoding="utf-8"
    )

    ignored_dirs = [".git", ".venv", "dist", "node_modules", "uploads"]
    for dirname in ignored_dirs:
        folder = tmp_path / dirname
        folder.mkdir()
        (folder / "hidden.py").write_text(
            f"{dirname}_SHOULD_NOT_APPEAR\n", encoding="utf-8"
        )

    result = scan_repository(tmp_path, "inspect visible source")

    assert "main.py" in result["discovered_files"]
    assert "VISIBLE_SOURCE_MARKER" in result["source_context"]

    for path in result["discovered_files"]:
        assert not any(path.startswith(f"{dirname}/") for dirname in ignored_dirs)


def test_scanner_skips_binary_content_from_ai_context(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_bytes(
        b"\x00BINARY_ONLY_MARKER\xff\xfe"
    )
    (tmp_path / "main.py").write_text(
        'print("VISIBLE_TEXT_MARKER")\n', encoding="utf-8"
    )

    result = scan_repository(tmp_path, "inspect Python source")

    assert "VISIBLE_TEXT_MARKER" in result["source_context"]
    assert "agent.py" not in result["files_in_context"]
    assert "BINARY_ONLY_MARKER" not in result["source_context"]


def test_scanner_truncates_oversized_files_and_preserves_ends(
    tmp_path: Path,
) -> None:
    source = (
        "HEAD_MARKER\n"
        + "MIDDLE_PAYLOAD_SHOULD_BE_TRUNCATED_" + ("x" * 120)
        + "\nTAIL_MARKER\n"
    )
    (tmp_path / "agent.py").write_text(source, encoding="utf-8")

    result = scan_repository(
        tmp_path,
        "inspect agent.py",
        max_file_chars=64,
    )
    context = result["source_context"]

    assert "HEAD_MARKER" in context
    assert "TAIL_MARKER" in context
    assert "middle omitted:" in context
    assert "MIDDLE_PAYLOAD_SHOULD_BE_TRUNCATED_" not in context


def test_scanner_respects_total_context_character_limit(
    tmp_path: Path,
) -> None:
    (tmp_path / "agent.py").write_text(
        "CORE_CODE_MARKER\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        "DOC_ONLY_MARKER\n" + ("documentation content " * 40),
        encoding="utf-8",
    )

    max_context_chars = 100
    result = scan_repository(
        tmp_path,
        "inspect project implementation",
        max_context_files=2,
        max_context_chars=max_context_chars,
    )

    assert "CORE_CODE_MARKER" in result["source_context"]
    assert "DOC_ONLY_MARKER" not in result["source_context"]
    assert len(result["source_context"]) <= max_context_chars
    assert result["files_in_context"] == ["agent.py"]


def test_scanner_does_not_modify_workspace_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        'print("READ_ONLY_MARKER")\n', encoding="utf-8"
    )
    (tmp_path / ".env").write_text(
        "SYNTHETIC_TEST_SECRET=do-not-read\n", encoding="utf-8"
    )
    generated = tmp_path / "node_modules"
    generated.mkdir()
    (generated / "package.js").write_text(
        "generated content\n", encoding="utf-8"
    )

    def snapshot_files(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and not path.is_symlink()
        }

    before = snapshot_files(tmp_path)
    result = scan_repository(tmp_path, "inspect main.py")
    after = snapshot_files(tmp_path)

    assert before == after
    assert "READ_ONLY_MARKER" in result["source_context"]
    assert "do-not-read" not in result["source_context"]
    assert "generated content" not in result["source_context"]
