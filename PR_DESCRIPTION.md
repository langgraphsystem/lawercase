# Hardening: JWT/RBAC + API Contract Alignment + Production Entrypoint

## Problem

Several production-facing issues existed simultaneously:

- Security gaps: critical routes (`/metrics`, document-monitor, AGUI) were previously callable without consistent JWT and role enforcement.
- Ownership gaps: document-monitor thread resources could be accessed without strict owner checks.
- Contract drift: frontend/backend route usage diverged (missing frontend `/cases` page, AGUI auth header mismatch, unregistered LLM routes).
- Deployment confusion: legacy `api/main_production.py` path and entrypoint drift from the canonical `api.main:app`.
- Documentation/testing drift: docs referenced stale paths and did not include a clear security coverage matrix.

## Solution Summary

### 1) Security hardening (JWT + RBAC + ownership)

- Implemented JWT verification and role checks in AGUI middleware.
- Enforced admin-only access for `/metrics`.
- Enforced JWT + ownership checks across document-monitor HTTP and WS endpoints.
- Added WS close-code handling:
  - `4401` unauthorized
  - `4403` forbidden
  - `4404` not found

### 2) API contract alignment

- Registered LLM router in `api.main` at `/v1/llm`.
- Removed legacy v1 (`agent/cases/memory/workflows`) routes from public `api.main` registration.
- Marked weakly used endpoints as `deprecated=True` (`/auth/me`, `/cases/statuses`, `/cases/{case_id}/restore`, `/cases/{case_id}/status`, `/v1/llm/stats`).
- Fixed frontend AGUI call to include auth headers.
- Added frontend `/cases` page (TODO placeholder) to resolve broken nav route.

### 3) Production entrypoint alignment

- Standardized Procfile to canonical entrypoint:
  - `uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- Removed deprecated duplicate entry module (`api/main_production.py`) from active path usage.

### 4) Reliability fix

- Fixed timezone-aware vs naive datetime handling in document monitor metadata calculation to prevent intermittent `500` in preview responses.

### 5) Documentation updates

- Updated `AGENTS.md` paths/structure to current repository reality.
- Updated `README.md` (entrypoint, JWT env vars, current API layout, legacy API policy).
- Added `docs/SECURITY_TEST_MATRIX.md` with explicit endpoint/scenario/status/test mapping.

## Files Changed

### Backend (main repo)

- `api/main.py`
- `Procfile`
- `api/main_production.py` (removed from active flow / deleted)
- `core/agui/middleware.py`
- `api/routes/metrics.py`
- `api/routes/document_monitor.py`
- `api/routes/health_production.py`
- `api/routes/agent.py`
- `api/routes/cases.py`
- `api/routes/memory.py`
- `api/routes/workflows.py`

### Tests

- `tests/test_jwt_auth_hardening.py`
- `tests/test_auth_security.py`
- `tests/test_auth_websocket_security.py`

### Docs

- `AGENTS.md`
- `README.md`
- `docs/SECURITY_TEST_MATRIX.md`

### Frontend (nested `web/` repo)

- `web/src/app/chat/page.tsx`
- `web/src/app/cases/page.tsx`

## Validation / Test Evidence

### Security + contract tests

- `pytest -q tests/test_jwt_auth_hardening.py` -> `6 passed`
- `pytest -q tests/test_auth_security.py tests/test_auth_websocket_security.py` -> `38 passed`

### Lint checks

- `ruff check tests/test_auth_security.py tests/test_auth_websocket_security.py api/routes/document_monitor.py` -> passed

### Entrypoint/runtime checks

- `python -m py_compile api/main.py` -> passed (validated in unrestricted mode due sandbox file-lock behavior)
- `uvicorn api.main:app --host 0.0.0.0 --port 8000` -> starts; `/health` returns `200`

## Risks

- Medium: removing legacy public registration can break external clients still calling old `/v1/*` endpoints.
- Frontend changes are split across nested `web/` repo and require coordinated PR/merge there.

## Rollback Plan

1. Revert this PR commit.
2. Restore previous Procfile command if needed.
3. If needed, temporarily remove strict checks by reverting:
   - `core/agui/middleware.py`
   - `api/routes/metrics.py`
   - `api/routes/document_monitor.py`
4. Keep test files to preserve regression visibility.

## Notes for Review

- Focus review on:
  - `core/agui/middleware.py`
  - `api/routes/document_monitor.py`
  - `tests/test_auth_security.py`
  - `tests/test_auth_websocket_security.py`
  - `docs/SECURITY_TEST_MATRIX.md`

- Legacy v1 endpoints are intentionally removed from public registration in this PR to avoid drift and accidental exposure.
