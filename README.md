# NexaPatch AI

## AI-Assisted Repository Inspection & Planning

NexaPatch AI is a developer-focused tool that inspects a local code repository, selects relevant source context, and generates an AI-assisted plan for understanding the codebase. It combines a React dashboard, FastAPI backend, repository scanning, secret-redaction safeguards, and a LangGraph workflow with optional Groq-powered AI planning.

The current version focuses on **read-only repository inspection and planning**. It does not automatically modify source files or execute shell commands.

## Overview

Understanding an unfamiliar repository can be time-consuming. Developers often need to identify important files, understand the project structure, and gather relevant context before planning changes.

NexaPatch AI provides a foundation for this workflow by scanning a configured local workspace, selecting bounded source context, and presenting the scan and planning results through a web dashboard.

## Key Features

- **Repository inspection:** Discover relevant files in a configured local workspace.
- **Read-only scanning:** Inspect a codebase without modifying files in the target repository.
- **Context selection:** Select bounded source context instead of sending the entire repository to the AI model.
- **Secret-redaction safeguards:** Exclude common secret/configuration files and attempt to redact common secret patterns from selected context.
- **LangGraph workflow:** Organize repository inspection and AI planning into workflow nodes.
- **Optional AI planning:** Use Groq's OpenAI-compatible chat completions API with configurable model settings.
- **React dashboard:** View real backend responses and the actual scan/AI execution status.
- **Run history:** Store local execution history in SQLite.
- **REST API:** Expose endpoints for health checks, agent runs, and run history.
- **Automated tests:** Validate important repository-scanner and backend behaviors.
- **Dependency checks:** Audit frontend dependencies for known vulnerabilities.

## How It Works

1. The user opens the NexaPatch dashboard.
2. The FastAPI backend loads the configured workspace.
3. The repository scanner discovers files and applies configured exclusions.
4. Relevant source context is selected within configured bounds, with secret-redaction safeguards applied.
5. The LangGraph workflow runs repository inspection and, when configured, AI planning.
6. The backend returns the execution status and results to the dashboard.
7. Run history is stored locally in SQLite.

AI planning requires valid provider configuration. If AI planning is unavailable or fails, the application reports the corresponding status instead of treating the run as a successful AI result.

## Architecture

```text
┌─────────────────────────┐
│   React + Vite UI       │
│   Repository Dashboard  │
└────────────┬────────────┘
             │ HTTP / REST
             ▼
┌─────────────────────────┐
│      FastAPI Backend    │
│   Health / Agent / Runs │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│   Repository Scanner    │
│  File Discovery &       │
│  Context Selection      │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│   LangGraph Workflow    │
│ Inspection → AI Planning│
└────────────┬────────────┘
             │ Optional provider request
             ▼
┌─────────────────────────┐
│  Groq API / Configured   │
│       AI Model           │
└─────────────────────────┘

Local run history → SQLite
```

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI, Uvicorn |
| AI workflow | LangGraph |
| AI provider | Groq OpenAI-compatible API |
| Repository inspection | Python file scanning and context selection |
| Secret safeguards | Secret-pattern detection and redaction |
| Run history | SQLite |
| Testing | Pytest |
| Frontend dependency management | npm |

## Project Structure

```text
nexapatch-ai/
├── .github/
│   └── workflows/              # GitHub Actions workflows
├── frontend/
│   ├── src/                    # React application source
│   ├── package.json
│   ├── package-lock.json
│   └── index.html
├── tests/                      # Automated backend tests
├── .env.example                # Example environment configuration
├── .gitignore
├── agent.py                    # FastAPI application and AI workflow
├── repository_scanner.py       # Repository discovery and context selection
├── secret_redaction.py         # Secret-redaction utilities
├── requirements.txt            # Python dependencies
└── README.md
```

## Getting Started

### Prerequisites

Install the following before running the project:

- Python and pip
- Node.js and npm
- Git
- A Groq API key if you want to enable AI planning

### 1. Clone the Repository

```bash
git clone https://github.com/BhanuStackDev/nexapatch-ai.git
cd nexapatch-ai
```

### 2. Set Up the Python Backend

Create a virtual environment.

**Windows PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a local `.env` file from `.env.example`, but only if a `.env` file does not already exist. Preserve your existing local configuration.

**Windows PowerShell**

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

Open `.env` and review the configuration:

```dotenv
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions
TARGET_REPO_PATH=.
CONVERSAI_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Configuration notes:

- `GROQ_API_KEY`: Your private API key. Keep it on the backend.
- `GROQ_MODEL`: The model identifier configured for planning. Check the provider's current supported-model list and use a model available to your account.
- `GROQ_API_URL`: The provider's compatible chat-completions endpoint.
- `TARGET_REPO_PATH`: The local repository or workspace to inspect. `.` refers to the current project root when the backend is launched from that directory.
- `CONVERSAI_CORS_ORIGINS`: The allowed development frontend origins.

To inspect a different local repository, set `TARGET_REPO_PATH` to its path. Use only repositories you are authorized to inspect.

Do not commit `.env` or place API keys in frontend source files.

### 4. Start the Backend

From the project root, with the Python virtual environment activated:

```bash
python -m uvicorn agent:app --reload --host 127.0.0.1 --port 8001
```

The API will be available at:

```text
http://127.0.0.1:8001
```

Interactive API documentation:

```text
http://127.0.0.1:8001/docs
```

### 5. Start the Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually:

```text
http://localhost:5173
```

The frontend uses `http://127.0.0.1:8001` as its default API URL. To override it, create `frontend/.env.local` with:

```dotenv
VITE_API_URL=http://127.0.0.1:8001
```

Restart the frontend development server after changing its environment variables.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend and workspace configuration |
| POST | `/api/run-agent` | Run repository inspection and attempt AI planning when configured |
| GET | `/api/runs?limit=10` | Retrieve recent execution history |
| GET | `/docs` | Open interactive API documentation |

### Execution Status

The backend reports the actual execution status:

- `scan_only`: Repository scanning worked, but AI planning was unavailable because the key or required AI configuration was missing.
- `ai_error`: AI planning encountered an error.
- A successful AI planning result should only be treated as successful when the returned response confirms it.

Responses also report the read-only state and mutation count. A scan or planning failure must not be interpreted as a successful AI run.

## Testing

### Run Backend Tests

From the project root:

```bash
python -m pytest -q
```

At the time of the latest local verification, the GitHub `main` version passed **18 backend tests**.

### Build the Frontend

From the project root:

```bash
cd frontend
npm run build
```

This generates the production frontend assets in `frontend/dist/`.

### Audit Frontend Dependencies

From the `frontend` directory:

```bash
npm audit --audit-level=high
```

The last checked dependency set returned zero vulnerabilities for this audit level. Dependency advisories can change over time, so run the audit again when updating packages.

## Security and Privacy

NexaPatch AI is currently a local-development portfolio project. Its repository scanner and AI workflow should be used with an understanding of the data being inspected.

- Never commit API keys, tokens, passwords, or private environment files.
- Common secret-file exclusions and secret-redaction patterns reduce exposure but cannot guarantee that every secret will be detected.
- Secrets can also occur in ordinary source files, comments, test fixtures, configuration files, or other text.
- When AI planning is enabled, selected source context may be sent to the configured AI provider. Review the target repository and data-handling requirements before enabling it.
- Inspect only repositories you are authorized to access.
- The backend is configured for loopback development. Do not expose it directly to the public internet as-is.
- Adding `.gitignore` rules does not remove files or secrets already present in Git history. Revoke and rotate any real credentials that were committed.

## Current Scope and Limitations

This release focuses on a read-only foundation for repository inspection and AI-assisted planning.

The following capabilities are **not implemented in the current phase**:

- Automatic source-code editing or patch application
- Shell command execution
- Running tests inside a target repository
- Creating commits or modifying Git branches in a target repository
- Multi-user authentication and authorization
- Streaming AI responses
- Production-hardened public deployment

These capabilities require additional engineering, including sandboxing, explicit authorization, reviewable changes, and stronger operational security.

## Roadmap

Potential next steps include:

- Improve the dashboard with richer scan summaries and file-level context visibility.
- Expand scanner and secret-redaction regression coverage.
- Improve error handling and AI-provider configuration feedback.
- Add a reviewable patch workflow with safe, isolated execution before enabling any write operations.
- Add authentication, authorization, and deployment hardening before considering remote multi-user use.
- Continue improving responsive layouts and accessibility.

## Contributing

Contributions, bug reports, and suggestions are welcome.

1. Fork the repository.
2. Create a focused feature branch.
3. Make and test your changes.
4. Open a pull request describing the change and its validation.

Please do not include real secrets, private repository data, or personal credentials in issues, test fixtures, or pull requests.

## License

No license has been specified in this repository yet. Unless a license is added, the default copyright protections apply; do not assume the project is available for unrestricted reuse.

---
### Developed & Designed by [Bhanuday Urmaliya](https://github.com/BhanuStackDev)

[GitHub Repository](https://github.com/BhanuStackDev/nexapatch-ai)
