"""API contract tests for the ConversAI read-only Phase 1 backend.

These tests replace the LangGraph object with a deterministic fake; they never
call Groq, inspect the real user repository, or execute project code.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import agent as agent_module


class FakeGraph:
    def __init__(self, result: dict[str, Any] | None = None, error: Exception | None = None):
        self.result = result or {}
        self.error = error
        self.last_state: dict[str, Any] | None = None

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        self.last_state = state
        if self.error:
            raise self.error
        return {**self.result, "request_text": state["request_text"], "repo_root": state["repo_root"]}


@pytest.fixture
def client() -> TestClient:
    with TestClient(agent_module.app) as test_client:
        yield test_client


def successful_result(root: Path) -> dict[str, Any]:
    return {
        "workspace_name": root.name,
        "repository_summary": "Workspace has two inspectable source files.",
        "total_files_found": 2,
        "inventory_truncated": False,
        "discovered_files": ["agent.py", "repository_scanner.py"],
        "files_in_context": ["agent.py", "repository_scanner.py"],
        "execution_plan": "1. Add API contract tests.\n2. Validate error handling.",
        "steps": ["Repository path validated", "AI plan generated with test-model"],
        "ai_used": True,
        "model": "test-model",
        "ai_error": "",
    }


def configure_test_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(agent_module, "DB_PATH", tmp_path / "test-data" / "runs.db")
    monkeypatch.setattr(agent_module, "TARGET_REPO_PATH", tmp_path)


def test_health_reports_workspace_and_read_only_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(agent_module, "TARGET_REPO_PATH", tmp_path)
    monkeypatch.setattr(agent_module, "GROQ_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setattr(agent_module, "GROQ_MODEL", "test-model")

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["workspace_configured"] is True
    assert body["workspace_name"] == tmp_path.name
    assert body["ai_configured"] is True
    assert body["mode"] == "read_only_inspection"


def test_run_agent_returns_plan_and_persists_history(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_test_storage(monkeypatch, tmp_path)
    fake_graph = FakeGraph(successful_result(tmp_path))
    monkeypatch.setattr(agent_module, "agent_graph", fake_graph)

    response = client.post(
        "/api/run-agent",
        json={"request_text": "Inspect API endpoints and propose tests."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "planned"
    assert body["ai_used"] is True
    assert body["execution_plan"].startswith("1. Add API contract tests")
    assert body["run_id"] is not None
    assert body["read_only"] is True
    assert body["mutations_performed"] == 0
    assert fake_graph.last_state is not None

    history_response = client.get("/api/runs?limit=10")
    assert history_response.status_code == 200
    runs = history_response.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == body["run_id"]
    assert runs[0]["status"] == "planned"


def test_run_agent_rejects_too_short_request(client: TestClient) -> None:
    response = client.post("/api/run-agent", json={"request_text": "no"})

    assert response.status_code == 422


def test_run_agent_returns_400_for_invalid_workspace(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_test_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(agent_module, "agent_graph", FakeGraph(error=ValueError("TARGET_REPO_PATH must point to an existing directory.")))

    response = client.post(
        "/api/run-agent",
        json={"request_text": "Inspect this missing repository."},
    )

    assert response.status_code == 400
    assert "existing directory" in response.json()["detail"]


def test_run_agent_reports_provider_failure_without_claiming_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_test_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(
        agent_module,
        "agent_graph",
        FakeGraph({
            **successful_result(tmp_path),
            "execution_plan": "AI planning failed. No files were modified.",
            "ai_used": False,
            "ai_error": "provider_timeout",
        }),
    )

    response = client.post(
        "/api/run-agent",
        json={"request_text": "Inspect the repository and summarize its design."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ai_error"
    assert body["ai_used"] is False
    assert body["ai_error"] == "provider_timeout"
    assert body["mutations_performed"] == 0


def test_run_agent_can_return_scan_only_when_key_is_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configure_test_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(
        agent_module,
        "agent_graph",
        FakeGraph({
            **successful_result(tmp_path),
            "execution_plan": "Repository scan completed; AI was not configured.",
            "ai_used": False,
            "ai_error": "missing_api_key",
        }),
    )

    response = client.post(
        "/api/run-agent",
        json={"request_text": "Inspect the repository without an AI plan."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scan_only"
    assert body["ai_used"] is False
    assert body["mutations_performed"] == 0

# DEPLOYMENT_READINESS_LOCALIZATION_TESTS

def test_localize_ui_returns_english_labels_without_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_module, "GROQ_API_KEY", "")
    labels = {"Agent console": "Agent console", "Run history": "Run history"}

    response = client.post(
        "/api/localize-ui",
        json={"target_language": "English", "labels": labels},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["labels"] == labels
    assert body["direction"] == "ltr"
    assert body["model"] is None
    assert body["translation_warning"] == ""


def test_localize_ui_rejects_empty_labels(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/localize-ui",
        json={"target_language": "Hindi", "labels": {}},
    )

    assert response.status_code == 422


def test_localize_ui_rejects_too_many_labels(
    client: TestClient,
) -> None:
    labels = {
        f"Label {index}": f"Value {index}"
        for index in range(agent_module.MAX_UI_LABELS + 1)
    }

    response = client.post(
        "/api/localize-ui",
        json={"target_language": "Hindi", "labels": labels},
    )

    assert response.status_code == 422


def test_localize_ui_rejects_oversized_label(
    client: TestClient,
) -> None:
    labels = {"Label": "x" * (agent_module.MAX_UI_LABEL_LENGTH + 1)}

    response = client.post(
        "/api/localize-ui",
        json={"target_language": "Hindi", "labels": labels},
    )

    assert response.status_code == 422


def test_localize_ui_requires_provider_for_non_english(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_module, "GROQ_API_KEY", "")

    response = client.post(
        "/api/localize-ui",
        json={
            "target_language": "Hindi",
            "labels": {"Agent console": "Agent console"},
        },
    )

    assert response.status_code == 503


def test_localize_ui_returns_cached_translation_without_provider_call(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    labels = {"Agent console": "Agent console", "Run history": "Run history"}
    translated = {
        "Agent console": "Agent console translated",
        "Run history": "Run history translated",
    }
    cache_key = agent_module.translation_cache_key("Hindi", labels)

    monkeypatch.setattr(agent_module, "GROQ_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setattr(agent_module, "GROQ_MODEL", "test-model")
    monkeypatch.setattr(
        agent_module,
        "UI_TRANSLATION_CACHE",
        agent_module.OrderedDict([(cache_key, translated)]),
    )

    response = client.post(
        "/api/localize-ui",
        json={"target_language": "Hindi", "labels": labels},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["labels"] == translated
    assert body["cached"] is True
    assert body["model"] == "test-model"

# DEPLOYMENT_READINESS_API_AUTH_TESTS

@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/run-agent", {"request_text": "Inspect this repository safely."}),
        ("post", "/api/localize-ui", {
            "target_language": "Hindi",
            "labels": {"Agent console": "Agent console"},
        }),
        ("get", "/api/runs?limit=1", None),
    ],
)
def test_sensitive_routes_reject_missing_bearer_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    monkeypatch.setattr(
        agent_module, "NEXAPATCH_API_TOKEN", "deployment-test-token"
    )

    response = getattr(client, method)(
        path,
        **({"json": payload} if payload is not None else {}),
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer wrong-test-token",
        "Basic deployment-test-token",
        "Bearer",
    ],
)
def test_sensitive_route_rejects_invalid_authorization(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    authorization: str,
) -> None:
    monkeypatch.setattr(
        agent_module, "NEXAPATCH_API_TOKEN", "deployment-test-token"
    )

    response = client.get(
        "/api/runs?limit=1",
        headers={"Authorization": authorization},
    )

    assert response.status_code == 401


def test_valid_bearer_token_allows_run_history(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        agent_module, "NEXAPATCH_API_TOKEN", "deployment-test-token"
    )
    configure_test_storage(monkeypatch, tmp_path)

    response = client.get(
        "/api/runs?limit=1",
        headers={"Authorization": "Bearer deployment-test-token"},
    )

    assert response.status_code == 200
    assert "runs" in response.json()


def test_health_reports_when_authentication_is_required(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        agent_module, "NEXAPATCH_API_TOKEN", "deployment-test-token"
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["auth_required"] is True
