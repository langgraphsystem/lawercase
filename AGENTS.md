# Repository Guidelines

## Deployment URLs (PRODUCTION)
- **Frontend (Vercel)**: https://eb1a-frontend.vercel.app/
- **Backend API (Railway)**: https://refreshing-reprieve-production-9802.up.railway.app
- **Frontend GitHub**: https://github.com/langgraphsystem/eb1a-frontend
- **Backend GitHub**: https://github.com/langgraphsystem/lawercase (branch: hardening/roadmap-v1)

## Frontend (Next.js 14 - eb1a-frontend repo)
Located in `web/` folder (separate git repo):
- `web/src/app/` — Next.js App Router pages (`/`, `/chat`, `/login`, `/cases`)
- `web/src/components/ui/` — shadcn/ui components
- `web/src/lib/agui.ts` — AG-UI types and API functions
- **Chat features**: Case selector dropdown, localStorage persistence per case
- **Deploy**: Push to main branch → Vercel auto-deploys

## Project Structure & Module Organization
- `core/` — agents (`groupagents`), memory system, LangGraph orchestration, RAG, security, workers, observability.
- `core/agui/` — AG-UI adapter for SSE streaming to frontend (adapter.py, events.py)
- `api/` — FastAPI app (`api.main:app`), middleware, metrics routes.
- `core/agui/middleware.py` — AG-UI endpoints and JWT/RBAC helpers (`/agui/run`, `/agui/agent`, `/agui/validation/submit`)
- `config/` — Pydantic settings, secrets manager, environment profiles.
- `deployment/` & `k8s/` — Dockerfiles, compose profiles, smoke tests, Kubernetes manifests.
- `recommendation_pipeline/`, `data/`, `out/` — EB-1A PDF pipeline assets and outputs.
- `tests/` — unit, integration (API, Telegram, memory), workflow/e2e, performance/load suites.

## Build, Test, and Development Commands
```bash
pip install -r requirements.txt                    # Base dependencies
ruff check . && black . --line-length 100          # Lint + format
pytest -q                                          # Fast suite (async supported)
pytest tests -vv --tb=short                        # Full local suite
uvicorn api.main:app --reload                      # Local API with .env
python app_demo.py                                 # LangGraph demo pipeline
python -m core.workers.task_worker smoke           # Worker smoke test
docker-compose up --build api worker               # Compose profile for API + worker
```

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indent, line length 100; type hints and docstrings for public APIs.
- Async-first I/O (`async def`), snake_case modules/functions, PascalCase classes, UPPER_SNAKE_CASE constants; async helpers often prefixed with `a` (e.g., `aretrieve`).
- Start modules with `from __future__ import annotations`; keep imports deterministic.
- Lint with `ruff check .`; format with `black --line-length 100`. Avoid new ignore rules unless justified.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio`, `hypothesis`, `respx`, `freezegun`; CI uses `CACHE_USE_FAKEREDIS=true`.
- Current layout keeps tests in `tests/test_*.py`; name files `test_*.py` and functions `test_*`.
- For API/Telegram flows, seed `.env` and reuse fixtures; prefer fake clients over live services.
- Run `pytest -vv --maxfail=1 --tb=short` before pushing; add regression cases with each bug fix.

## Commit & Pull Request Guidelines
- Use Conventional Commit prefixes (`feat:`, `fix:`, `chore:`, `docs:`, `test:`); keep scopes concise.
- PRs: problem/solution summary, key files touched, test commands run, risk/rollback, linked issues. Follow `PR_DESCRIPTION.md` when relevant.
- Keep CI green locally (ruff, pytest, pip-audit if deps change); attach logs or screenshots for user-facing changes.

## Security & Configuration Tips
- Store secrets in `.env` / `env/*.env` and load via `config/secrets_manager.py`; never commit keys. Gitleaks runs in CI.
- Keep RBAC and prompt-injection guards on by default (`RBAC_POLICY_PATH`, `PROMPT_DETECTION_ENABLED`); respect API rate limits (`API_RATE_LIMIT`, `API_RATE_WINDOW`).
- Enable tracing/logging via env vars instead of code tweaks; ensure audit trail path (`AUDIT_LOG_PATH`) is writable in deployments.
