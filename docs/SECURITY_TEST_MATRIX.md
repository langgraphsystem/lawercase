# Security Test Matrix

This matrix tracks API authn/authz and ownership checks validated by automated tests.

## Scope
- `tests/test_auth_security.py`
- `tests/test_auth_websocket_security.py`

## Covered Scenarios

| Endpoint | Protocol | Scenario | Expected | Test | Status |
|---|---|---|---|---|---|
| `/metrics` | HTTP | No token | `401` | `test_unauthorized_access` | Covered |
| `/metrics` | HTTP | Invalid JWT | `401` | `test_invalid_token` | Covered |
| `/metrics` | HTTP | Valid JWT, role=`user` | `403` | `test_wrong_role` | Covered |
| `/metrics` | HTTP | Valid JWT, role=`admin` | `200` | `test_admin_access` | Covered |
| `/api/document/preview/{thread_id}` | HTTP | Foreign owner access | `403` | `test_ownership_check` | Covered |
| `/api/document/preview/{thread_id}` | HTTP | Owner access | `200` | `test_own_resource_access` | Covered |
| `/api/document/preview/{thread_id}` | HTTP | Owner access with timezone-aware `started_at` | `200` | `test_own_resource_access_with_timezone_started_at` | Covered |
| `/agui/agent` | HTTP | No token | `401` | `test_agui_agent_unauthorized_access` | Covered |
| `/agui/agent` | HTTP | Invalid JWT | `401` | `test_agui_agent_invalid_token` | Covered |
| `/agui/run` | HTTP | No token | `401` | `test_agui_run_unauthorized_access` | Covered |
| `/agui/run` | HTTP | JWT `user_id` mismatch in payload | `403` | `test_agui_run_user_id_mismatch_returns_403` | Covered |
| `/agui/run` | HTTP | Valid owner request | `200` | `test_agui_run_owner_access_returns_200` | Covered |
| `/agui/validation/submit` | HTTP | No token | `401` | `test_agui_validation_unauthorized_access` | Covered |
| `/agui/validation/submit` | HTTP | Invalid JWT | `401` | `test_agui_validation_invalid_token` | Covered |
| `/agui/validation/submit` | HTTP | Valid request | `200` | `test_agui_validation_valid_access` | Covered |
| `/v1/llm/models` | HTTP | Models endpoint available | `200` | `test_llm_models_available` | Covered |
| `/v1/llm/generate` | HTTP | Unknown provider validation | `400` | `test_llm_generate_unknown_provider_returns_400` | Covered |
| `/v1/llm/generate` | HTTP | Happy-path generation via mocked provider | `200` | `test_llm_generate_happy_path_returns_200` | Covered |
| `/v1/llm/generate/stream` | HTTP | Happy-path SSE generation via mocked provider | `200` + `text/event-stream` | `test_llm_generate_stream_happy_path_returns_sse` | Covered |
| `/v1/agent/process` | HTTP | Legacy v1 route removed from public contract | `404` | `test_legacy_endpoints_removed_from_public_contract[/v1/agent/process]` | Covered |
| `/v1/cases` | HTTP | Legacy v1 route removed from public contract | `404` | `test_legacy_endpoints_removed_from_public_contract[/v1/cases]` | Covered |
| `/v1/memory/stats` | HTTP | Legacy v1 route removed from public contract | `404` | `test_legacy_endpoints_removed_from_public_contract[/v1/memory/stats]` | Covered |
| `/v1/workflows` | HTTP | Legacy v1 route removed from public contract | `404` | `test_legacy_endpoints_removed_from_public_contract[/v1/workflows]` | Covered |
| `/api/generate-petition` | HTTP | No token | `401` | `test_generate_petition_unauthorized_access` | Covered |
| `/api/upload-exhibit/{thread_id}` | HTTP | No token | `401` | `test_upload_exhibit_unauthorized_access` | Covered |
| `/api/upload-exhibit/{thread_id}` | HTTP | Foreign owner access | `403` | `test_upload_exhibit_foreign_thread_returns_403` | Covered |
| `/api/download-petition-pdf/{thread_id}` | HTTP | No token | `401` | `test_download_petition_pdf_unauthorized_access` | Covered |
| `/api/download-petition-pdf/{thread_id}` | HTTP | Foreign owner access | `403` | `test_download_petition_pdf_foreign_thread_returns_403` | Covered |
| `/api/pause/{thread_id}` | HTTP | No token | `401` | `test_pause_unauthorized_access` | Covered |
| `/api/pause/{thread_id}` | HTTP | Foreign owner access | `403` | `test_pause_foreign_thread_returns_403` | Covered |
| `/api/resume/{thread_id}` | HTTP | No token | `401` | `test_resume_unauthorized_access` | Covered |
| `/api/resume/{thread_id}` | HTTP | Foreign owner access | `403` | `test_resume_foreign_thread_returns_403` | Covered |
| `/agui/ws/{case_id}` | WS | No token on connect | close `4401` | `test_agui_ws_without_token_close_4401` | Covered |
| `/agui/ws/{case_id}` | WS | Invalid token on connect | close `4401` | `test_agui_ws_invalid_token_close_4401` | Covered |
| `/api/ws/document/{thread_id}` | WS | No token on connect | close `4401` | `test_document_ws_without_token_close_4401` | Covered |
| `/api/ws/document/{thread_id}` | WS | Foreign owner thread | close `4403` | `test_document_ws_foreign_thread_close_4403` | Covered |
| `/api/ws/document/{thread_id}` | WS | Missing thread | close `4404` | `test_document_ws_missing_thread_close_4404` | Covered |
| `/api/ws/document/{thread_id}` | WS | Owner connect success | connected message | `test_document_ws_owner_connected` | Covered |

## Current Gaps

No open P0 auth/ownership gaps for current HTTP + WS security scope.

## Run

```bash
pytest -q tests/test_auth_security.py tests/test_auth_websocket_security.py
```
