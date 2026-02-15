# API Contract Audit

Дата аудита: 2026-02-13

Покрытие:
- Backend: `api/main.py` + подключенные роутеры
- Frontend: `web/src/lib/agui.ts`, `web/src/lib/auth.ts`, `web/src/app/chat/page.tsx`, `web/src/app/cases/page.tsx`

## Проверка соответствия frontend/backend

- LLM-роуты зарегистрированы и доступны: `POST /v1/llm/generate`, `POST /v1/llm/generate/stream`, `GET /v1/llm/models`, `GET /v1/llm/stats`.
- Маршрут `/cases` на фронте имеет backend-обработчики: `GET /cases`, `POST /cases`, `GET /cases/{case_id}` и др.
- Битых ссылок фронта на несуществующие backend-маршруты не обнаружено.

## Матрица изменений

| Эндпоинт | Статус | Что изменено |
|---|---|---|
| `POST /auth/login` | ок | Используется фронтом (`login`). |
| `GET /cases` | ок | Используется фронтом (`fetchCases`). |
| `GET /cases/{case_id}` | ок | Контракт существует, используется helper-методом `fetchCase`. |
| `POST /agui/agent` | исправлен | Используется фронтом; подтверждена JWT-защита и owner checks в AGUI middleware. |
| `POST /agui/run` | ок | Контракт зарегистрирован и защищён JWT. |
| `GET /metrics` | исправлен | JWT + `require_role("admin")`; без токена `401`, c role `user` -> `403`. |
| `GET /api/document/preview/{thread_id}` | исправлен | JWT + ownership (`user_id` токена против владельца thread). |
| `POST /api/upload-exhibit/{thread_id}` | исправлен | JWT + ownership проверки. |
| `GET /api/download-petition-pdf/{thread_id}` | исправлен | JWT + ownership проверки. |
| `POST /api/pause/{thread_id}` | исправлен | JWT + ownership проверки. |
| `POST /api/resume/{thread_id}` | исправлен | JWT + ownership проверки. |
| `POST /v1/llm/generate` | добавлен | Роутер `llm` зарегистрирован в `api.main` (prefix `/v1/llm`). |
| `POST /v1/llm/generate/stream` | добавлен | Роутер `llm` зарегистрирован в `api.main` (prefix `/v1/llm`). |
| `GET /v1/llm/models` | добавлен | Роутер `llm` зарегистрирован в `api.main` (prefix `/v1/llm`). |
| `GET /v1/llm/stats` | исправлен | Помечен как `deprecated`, так как endpoint не используется фронтом и возвращает placeholder-ответ. |
| `GET /auth/me` | исправлен | Помечен как `deprecated` (не используется фронтом). |
| `GET /cases/statuses` | исправлен | Помечен как `deprecated` (не используется фронтом). |
| `POST /cases/{case_id}/restore` | исправлен | Помечен как `deprecated` (не используется фронтом). |
| `PATCH /cases/{case_id}/status` | исправлен | Помечен как `deprecated` (не используется фронтом). |
| `POST /v1/agent/process` | удалён | Legacy v1 endpoint больше не зарегистрирован в публичном `api.main`. |
| `GET /v1/cases` | удалён | Legacy v1 endpoint больше не зарегистрирован в публичном `api.main`. |
| `GET /v1/memory/stats` | удалён | Legacy v1 endpoint больше не зарегистрирован в публичном `api.main`. |
| `GET /v1/workflows` | удалён | Legacy v1 endpoint больше не зарегистрирован в публичном `api.main`. |

## Технические примечания

- Deprecated-эндпоинты оставлены для мягкой миграции клиентов и отображаются в OpenAPI как устаревшие.
- Legacy v1 роуты удалены именно из публичной регистрации (`api.main`), чтобы не оставлять «случайно открытый» контракт.

## Полный список зарегистрированных эндпоинтов (`api.main`)

| Метод | Путь | Используется фронтом |
|---|---|---|
| `POST` | `/agui/agent` | да |
| `GET` | `/agui/health` | нет |
| `POST` | `/agui/run` | да |
| `POST` | `/agui/validation/submit` | нет |
| `GET` | `/api/document/preview/{thread_id}` | нет |
| `GET` | `/api/download-petition-pdf/{thread_id}` | нет |
| `POST` | `/api/generate-petition` | нет |
| `POST` | `/api/pause/{thread_id}` | нет |
| `POST` | `/api/resume/{thread_id}` | нет |
| `POST` | `/api/upload-exhibit/{thread_id}` | нет |
| `POST` | `/auth/login` | да |
| `GET` | `/auth/me` | нет |
| `GET` | `/cases` | да |
| `POST` | `/cases` | нет |
| `GET` | `/cases/statuses` | нет |
| `DELETE` | `/cases/{case_id}` | нет |
| `GET` | `/cases/{case_id}` | да (через helper) |
| `PUT` | `/cases/{case_id}` | нет |
| `POST` | `/cases/{case_id}/restore` | нет |
| `PATCH` | `/cases/{case_id}/status` | нет |
| `GET` | `/health` | нет |
| `GET` | `/metrics` | нет |
| `GET` | `/ready` | нет |
| `POST` | `/telegram/webhook` | нет |
| `POST` | `/v1/llm/generate` | нет |
| `POST` | `/v1/llm/generate/stream` | нет |
| `GET` | `/v1/llm/models` | нет |
| `GET` | `/v1/llm/stats` | нет |
| `GET` | `/docs` | нет (dev only) |
| `GET` | `/redoc` | нет (dev only) |
| `GET` | `/openapi.json` | нет (dev only) |
