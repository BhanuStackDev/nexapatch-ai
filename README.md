# NexaPatch — Phase 1 Foundation

This patch replaces the hard-coded demo response with a real **read-only repository scanner**, a **LangGraph workflow**, optional **Groq AI planning**, and a frontend connected to the FastAPI backend.

## What this phase includes

- Read-only file discovery in a configured local workspace.
- Exclusion of common generated/dependency directories and common secret/config files (`.env`, key/certificate files, databases, etc.).
- Bounded source-context selection; it does not send the entire repository to the model.
- LangGraph nodes for repository inspection and AI planning.
- Groq OpenAI-compatible chat completions with configurable model ID.
- SQLite run history stored in ignored local `data/agent_runs.db`.
- React dashboard that uses real API calls and reports actual scan/AI status.
- Unit tests for scanner behavior.

**Not included yet:** code editing, shell command execution, test execution against target repositories, Git changes, multi-user authentication, and streaming. The backend binds to loopback for local development. Do not expose this API to the public internet as-is.

## Apply to your existing repository (Windows PowerShell)

1. Open your local `nexapatch-ai` repository folder and create a branch:
   ```powershell
   git checkout -b feat/real-repository-inspection
   ```
2. Back up or commit your current work. Extract this ZIP directly into the repository root and choose **merge/replace** for the supplied files. The ZIP mirrors the repo layout: `agent.py`, `repository_scanner.py`, `requirements.txt`, `.gitignore`, `frontend/src/App.jsx`, `frontend/src/index.css`, and `tests/`.
3. Create/update your local `.env` file. Since your current repo already has a `.env`, open that file and update the values instead of assuming copying the example will overwrite it:
   ```env
   GROQ_API_KEY=your_real_groq_api_key_here
   GROQ_MODEL=qwen/qwen3.8-27b
   GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions
   TARGET_REPO_PATH=.
   CONVERSAI_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```
   Use your own key from Groq's console. **Never** put the key in a React file or commit `.env`. If you want to inspect another local repository, point `TARGET_REPO_PATH` to that folder. Relative paths are resolved from the terminal's current working directory, so run the backend from the repository root for `TARGET_REPO_PATH=.`.
4. From the repository root, install the backend dependencies and run the scanner tests:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   python -m pytest tests -q
   ```
5. Start the backend from the repository root:
   ```powershell
   python -m uvicorn agent:app --reload --host 127.0.0.1 --port 8001
   ```
6. Open a **second terminal** and start the frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
   Open the local Vite URL shown in the terminal (usually `http://localhost:5173`). The default frontend API URL is `http://127.0.0.1:8001`; you can override it with `frontend/.env.local`:
   ```env
   VITE_API_URL=http://127.0.0.1:8001
   ```

## API endpoints

- `GET /api/health` — backend, workspace and model configuration status.
- `POST /api/run-agent` — scan the configured repository and produce an AI plan when a Groq key is configured.
- `GET /api/runs?limit=10` — recent scan history.
- `GET /docs` — interactive OpenAPI docs.

`status=scan_only` means repository scanning worked but an AI key is missing. `status=ai_error` means planning failed. Neither should be presented as a successful AI run. Every response states `read_only=true` and `mutations_performed=0`.

## Git hygiene: do this before pushing

If `.env` or a local SQLite database has been committed, adding it to `.gitignore` does **not** remove it from existing commits. Review the tracked files:
```powershell
git ls-files .env agent_execution_logs.db
```
If `.env` is tracked, untrack it while preserving your local copy:
```powershell
git rm --cached .env
```
If the SQLite DB is tracked, back it up if needed and untrack it:
```powershell
git rm --cached agent_execution_logs.db
```
If a real API key was ever committed, revoke/rotate it. Then review the diff before committing:
```powershell
git status --short
git diff --check
git diff
```

## Provider/model configuration

The example model is `qwen/qwen3.8-27b`. Model availability changes, so check Groq's official supported-model list and choose an active model available for your account: https://console.groq.com/docs/models

## Security note

The scanner tries to exclude common secret files, but secrets can also be embedded in ordinary source files. Review the selected files and never point the tool at a sensitive repository without understanding that selected source context is sent to the configured AI provider. This is a local-development portfolio foundation, not a production-safe remote service. Phase 2 must add sandboxed writes/execution and stronger authorization before any code-editing feature is enabled.
