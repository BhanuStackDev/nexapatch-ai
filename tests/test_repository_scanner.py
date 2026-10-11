from pathlib import Path

from repository_scanner import scan_repository


def test_scanner_finds_source_files_and_skips_secrets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Demo project", encoding="utf-8")
    (tmp_path / "main.py").write_text("def greet():\n    return 'hello'\n", encoding="utf-8")
    (tmp_path / ".env").write_text("GROQ_API_KEY=super-secret-value", encoding="utf-8")
    (tmp_path / "private.pem").write_text("PRIVATE KEY MATERIAL", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "hidden.js").write_text("should not be indexed", encoding="utf-8")

    result = scan_repository(tmp_path, "review main.py for bugs")

    assert "README.md" in result["discovered_files"]
    assert "main.py" in result["discovered_files"]
    assert ".env" not in result["discovered_files"]
    assert "private.pem" not in result["discovered_files"]
    assert not any("node_modules" in path for path in result["discovered_files"])
    assert "super-secret-value" not in result["source_context"]
    assert "def greet" in result["source_context"]


def test_scanner_rejects_nonexistent_root(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    try:
        scan_repository(missing, "inspect this project")
    except ValueError as exc:
        assert "existing directory" in str(exc)
    else:
        raise AssertionError("Expected ValueError for a non-existent workspace")


def test_core_implementation_files_are_prioritized_over_readmes(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("General project description", encoding="utf-8")
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "src").mkdir()
    (tmp_path / "frontend" / "src" / "main.jsx").write_text("createRoot()", encoding="utf-8")
    (tmp_path / "frontend" / "src" / "App.jsx").write_text("export default function App() {}", encoding="utf-8")
    (tmp_path / "frontend" / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    (tmp_path / "agent.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n" + "# implementation detail\n" * 100 +
        "@app.post('/api/run-agent')\nasync def run_agent():\n    return {}\n",
        encoding="utf-8",
    )
    (tmp_path / "repository_scanner.py").write_text("def scan_repository(): pass", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_repository_scanner.py").write_text("def test_scan(): pass", encoding="utf-8")
    (tmp_path / "frontend" / "README.md").write_text("Frontend documentation", encoding="utf-8")

    result = scan_repository(tmp_path, "inspect API and frontend", max_context_files=6)

    assert "agent.py" in result["files_in_context"]
    assert "repository_scanner.py" in result["files_in_context"]
    assert "frontend/src/App.jsx" in result["files_in_context"]
    assert "frontend/README.md" not in result["files_in_context"]
    assert "/api/run-agent" in result["source_context"]
