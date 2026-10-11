from pathlib import Path

from repository_scanner import scan_repository


def test_scanner_redacts_inline_credentials_and_common_tokens(
    tmp_path: Path,
) -> None:
    groq_key = "gsk_" + "A" * 32
    database_password = "database-password-" + "B" * 16
    api_key = "sk-proj-" + "C" * 32
    bearer_token = "bearer-sensitive-token-123456"
    github_token = "ghp_" + "D" * 32
    jwt_token = "eyJ" + "E" * 12 + "." + "F" * 12 + "." + "G" * 12

    source = (
        f'GROQ_API_KEY = "{groq_key}"\n'
        f"DB_PASSWORD = '{database_password}'\n"
        f'apiKey = "{api_key}"\n'
        f"# copied header: Authorization: Bearer {bearer_token}\n"
        f"# pasted token: {github_token}\n"
        f"# pasted JWT: {jwt_token}\n"
        'def safe_function():\n    return "SAFE_MARKER"\n'
    )
    (tmp_path / "main.py").write_text(source, encoding="utf-8")

    result = scan_repository(tmp_path, "inspect main.py for security issues")
    assert "main.py" in result["files_in_context"]
    context = result["source_context"]

    for secret in (
        groq_key, database_password, api_key, bearer_token, github_token, jwt_token
    ):
        assert secret not in context

    assert "SAFE_MARKER" in context
    assert "[REDACTED" in context


def test_scanner_redacts_private_key_block_embedded_in_source(
    tmp_path: Path,
) -> None:
    private_payload = "SYNTHETIC_PRIVATE_KEY_PAYLOAD_DO_NOT_LEAK"
    source = (
        'APP_NAME = "NexaPatch"\n'
        "-----BEGIN PRIVATE KEY-----\n"
        f"{private_payload}\n"
        "-----END PRIVATE KEY-----\n"
    )
    (tmp_path / "main.py").write_text(source, encoding="utf-8")

    result = scan_repository(tmp_path, "inspect main.py")
    assert private_payload not in result["source_context"]
    assert "[REDACTED PRIVATE KEY]" in result["source_context"]
    assert "NexaPatch" in result["source_context"]


def test_scanner_preserves_unrelated_source_text(tmp_path: Path) -> None:
    source = (
        'APP_NAME = "NexaPatch"\n'
        "def add(left, right):\n"
        "    return left + right\n"
    )
    (tmp_path / "main.py").write_text(source, encoding="utf-8")

    result = scan_repository(tmp_path, "review the add function")
    assert 'APP_NAME = "NexaPatch"' in result["source_context"]
    assert "return left + right" in result["source_context"]

def test_scanner_redacts_json_quoted_secret_keys(tmp_path: Path) -> None:
    json_secret = "json-config-secret-" + "H" * 16
    source = '{"token": "' + json_secret + '"}' + "\n"
    (tmp_path / "config.py").write_text(source, encoding="utf-8")

    result = scan_repository(tmp_path, "inspect config")
    context = result["source_context"]

    assert json_secret not in context
    assert "[REDACTED]" in context
