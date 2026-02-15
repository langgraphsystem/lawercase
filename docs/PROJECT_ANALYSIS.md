# MegaAgent Pro Project Analysis (EB-1A) - 2025-12-15
<!--
NOTE: This document starts with ASCII-only lines intentionally to avoid UTF-8
boundary issues in some Windows toolchains. Russian content follows below.
-->

## Summary (EN, short)
- Repository contains a FastAPI backend, a Next.js 14 frontend (in `web/`), multi-agent orchestration (MegaAgent), LangGraph workflows, a memory subsystem (Supabase/Postgres/pgvector), RAG pipeline, Telegram bot integration, and deployment assets (Docker/Railway/K8s).

---

## 1) Назначение проекта (что это)
Проект представляет собой систему для сопровождения иммиграционных кейсов (в первую очередь EB-1A) с использованием:
- мультиагентной оркестрации (MegaAgent + специализированные агенты),
- workflow/графов (LangGraph) для пошаговых процедур,
- памяти/хранилищ (эпизодическая, семантическая, рабочая память/RMT),
- RAG-пайплайна (chunking + sparse/dense + hybrid fusion + rerank),
- API (FastAPI) для интеграций (веб-фронтенд, Telegram, мониторинг),
- AG-UI протокола для стриминга событий/ответов (SSE/WebSocket).

В репозитории также присутствуют инструменты для генерации/сборки PDF-пакетов (петиции/эксибиты), мониторинг генерации документов (UI + WebSocket), инфраструктурные манифесты (Docker/Compose/Railway/K8s), а также крупный набор документации и тестов.

## 2) Продакшен URL и репозитории
Согласно `AGENTS.md`:
- Frontend (Vercel): https://eb1a-frontend.vercel.app/
- Backend API (Railway): https://refreshing-reprieve-production-9802.up.railway.app
- Frontend GitHub: https://github.com/langgraphsystem/eb1a-frontend (в этом workspace также есть копия в `web/`)
- Backend GitHub: https://github.com/langgraphsystem/lawercase (ветка: `hardening/roadmap-v1`)

## 3) Структура репозитория (ключевые зоны)
Наблюдаемая верхнеуровневая структура:
- `api/` — FastAPI приложение (dev и production варианты), роуты, middleware.
- `core/` — основная логика: агенты, memory, orchestration (LangGraph), RAG, security, tools, observability, storage.
- `telegram_interface/` — Telegram bot интеграция (webhook/handlers).
- `recommendation_pipeline/` — PDF/ocr/index/assembler pipeline.
- `deployment/`, `k8s/` — Docker/Kubernetes инфраструктура.
- `tests/` — unit/integration/workflows/e2e/performance и др.
- `web/` — Next.js 14 фронтенд (отдельный git-репозиторий внутри, с `node_modules`/`.next`).
- множество `.md` отчётов/гайдов (история внедрения, статусы, планы).

## 4) Архитектура (схема компонентов и потоков)
Упрощённо:
1) Frontend (Next.js) (`web/`) -> запросы в Backend API (Railway).
2) Backend:
   - обычные REST эндпоинты (кейсы/память/LLM/health),
   - AG-UI SSE (`/agui/run`, `/agui/agent`) для стриминга событий,
   - Document Monitor (`/api/...` + WebSocket) для мониторинга генерации документов,
   - Telegram webhook (`/telegram/webhook`) и связанные сервисы.
3) Внутри backend: DI container создаёт и раздаёт единые инстансы (MegaAgent, MemoryManager, LLM router, MCP manager).
4) MegaAgent маршрутизирует команду -> агенты/воркфлоу/инструменты -> пишет аудит-события -> отвечает.
5) Memory по умолчанию ориентирована на Supabase/Postgres-backed хранилища (семантика/эпизодика/working/RMT) + доп. кэши/Redis.
6) LangGraph workflows инкапсулируют многошаговые процедуры (в т.ч. EB-1A).

## 5) Backend API: точки входа, роутинг, стриминг
### 5.1 Два варианта FastAPI приложения
В репозитории одновременно существуют два "entrypoint"-приложения:
- `api/main.py` — универсальный app: подключает роуты, AG-UI, Telegram webhook и монтирует `StaticFiles` на `/` (если найден `index.html` в корне).
- `api/main_production.py` — production-ready app: отдельный набор middleware, health-эндпоинты (`/liveness`, `/readiness`, `/startup`), расширенное логирование/метрики, интеграция `core.config.production_settings`.

Важно для эксплуатации: `Dockerfile`/`railway.json` по умолчанию стартуют `api.main:app`, а K8s манифесты ожидают эндпоинты вроде `/readiness` и `/liveness` (они определены в production-ветке).

### 5.2 Основные роуты в `api/main.py`
Подключены роуты:
- `api/routes/health.py`: `GET /health`, `GET /ready`.
- `api/routes/agent.py`: `POST /v1/ask`, `/v1/search`, `/v1/tool`, `/v1/agent/command`.
- `api/routes/cases.py`: `POST /v1/case/{action}` (обёртка поверх MegaAgent CommandType.CASE).
- `api/routes/memory.py`: `/v1/memory/snapshot|write|retrieve`.
- `api/routes/metrics.py`: `GET /metrics`.
- `api/routes/workflows.py`: `GET /v1/workflows/health`.
- `api/routes/document_monitor.py`: `/api/...` + websocket.
- `core/agui/middleware.py`: `/agui/run`, `/agui/agent`, `/agui/validation/submit`, `/agui/health` (+ опционально websocket).
Также: `POST /telegram/webhook` (секрет в `X-Telegram-Bot-Api-Secret-Token`), и монтирование `/sites` + (опционально) статики на `/`.

### 5.3 AG-UI протокол
Реализация в `core/agui/`:
- `core/agui/events.py` — типы событий (RUN_*, TEXT_*, STATE_*, TOOL_*, STEP_*, VALIDATION_*, DOCUMENT_GENERATED и др.), сериализация в SSE.
- `core/agui/adapter.py` — обёртка над запуском workflow/агентов, эмитит события.
- `core/agui/middleware.py` — FastAPI router `/agui/*` с `StreamingResponse`.

## 6) DI контейнер и основная оркестрация
### 6.1 DI контейнер
`core/di/container.py`:
- хранит singletons/factories,
- создаёт по умолчанию:
  - `memory_manager` (на Supabase stores),
  - `tool_registry`,
  - `mcp_manager` (MCP tools),
  - `llm_router` (IntelligentRouter поверх провайдеров),
  - factory `mega_agent` (создаёт MegaAgent с injected зависимостями).

### 6.2 MegaAgent
`core/groupagents/mega_agent.py` — центральный оркестратор:
- принимает `MegaAgentCommand` (тип/действие/payload),
- выполняет RBAC/безопасность (модуль `core/security`),
- может использовать LLM router и "secure sandbox" (пока как каркас в `core/execution/secure_sandbox.py`),
- пишет audit события в memory,
- маршрутизирует по агентам (CaseAgent/WriterAgent/ValidatorAgent/SupervisorAgent/EB1Agent и т.д. — см. `core/groupagents/`).

## 7) Workflows (LangGraph) и EB-1A логика
`core/orchestration/pipeline_manager.py`:
- сборка/компиляция графов (Memory workflow, Enhanced workflow, EB-1A workflow),
- checkpointer: in-memory или SQLite (`langgraph.checkpoint.sqlite.SqliteSaver`).

`core/orchestration/workflow_graph.py`:
- `WorkflowState` (единое состояние для многошаговых процедур),
- ноды/роутинг для EB-1A процедуры (eligibility -> evidence -> criteria -> strength -> gaps -> docs -> validation -> human_review -> finalize),
- audit-логирование шагов через memory.

## 8) Память, хранилища и БД
### 8.1 MemoryManager
Есть две реализации/ветки:
- `core/memory/memory_manager.py` — "SUPABASE-ONLY" по умолчанию (semantic/episodic/working на Supabase-store), embedder по умолчанию No-op.
- `core/memory/memory_manager_v2.py` — "Supabase-first" с `DeterministicEmbedder` по умолчанию и фабриками для Pinecone/Postgres/Dev.

Фактически DI контейнер (`core/di/container.py`) использует `core/memory/memory_manager.py`, а `api/deps.py` имеет отдельную функцию `get_memory_manager()` на базе v2 (но роуты берут MegaAgent из DI).

### 8.2 Postgres/pgvector и Alembic
- `core/storage/connection.py` — async SQLAlchemy engine с параметрами для Supabase/PgBouncer (в т.ч. `statement_cache_size=0`).
- `core/storage/supabase_vector_store.py` — низкоуровневый pgvector-поиск по cosine distance.
- `alembic/` + `alembic.ini` + `migrations/*.sql` — миграции/скрипты, включая `CREATE EXTENSION vector` и схему `mega_agent`.

### 8.3 Redis
Встречается в `docker-compose.yml` и `core/storage/redis_client.py` (и health checks в `api/routes/health_production.py`).

## 9) RAG подсистема
`core/rag/` реализует гибридный RAG:
- chunking стратегии (`core/rag/chunking.py`),
- sparse retrieval (BM25) (`core/rag/sparse_retrieval.py`),
- dense/hybrid/fusion (`core/rag/hybrid.py`, `core/rag/fusion.py`),
- rerank (`core/rag/reranker.py`),
- сборка контекста (`core/rag/pipeline.py`).

Также есть отдельный ingestion-контур (`core/rag/ingestion.py`) с chunking по токенам и батч-обработкой.

## 10) Document Monitor (UI + API + WebSocket)
`api/routes/document_monitor.py`:
- REST эндпоинты для запуска генерации/получения статуса/загрузки эксибитов,
- WebSocket `/api/ws/document/{thread_id}` для push-обновлений,
- хранение состояния через `core/storage/document_workflow_store.py`,
- генерация PDF через `weasyprint` (если доступен), иначе fallback в HTML.

UI для мониторинга лежит в корне (`index.html`) и может быть смонтирован FastAPI как статика.

## 11) Frontend (Next.js 14) и интеграция с backend
`web/` — Next.js 14 + shadcn/ui.
- `web/src/lib/agui.ts` — типы AG-UI, SSE-клиент `createAGUIStream()`, базовый URL берётся из `NEXT_PUBLIC_API_URL` (или дефолтится на Railway URL).
- `web/src/app/chat/page.tsx` — чат-страница: выбирает кейс, хранит историю в `localStorage` per case, читает события AG-UI и стримит ответ.

Наблюдение по контрактам:
- фронтенд вызывает `GET ${API_BASE_URL}/cases` и `GET ${API_BASE_URL}/cases/{id}` (см. `web/src/lib/agui.ts`).
- в backend-ветке `api/main.py` "прямого" `/cases` нет; CRUD-роутер для кейсов реализован в `api/routes/case_management.py`, но он подключается в `api/main_production.py` под префиксом `.../api/v1/cases` (а не `/cases`).
Это потенциальная зона рассогласования между текущим backend entrypoint и ожиданиями фронтенда.

## 12) Деплой (Docker / Railway / K8s)
### 12.1 Docker
- `Dockerfile` multi-stage: targets `api`, `bot`, `worker`.
- `docker-compose.yml`: postgres + redis + api + worker (profile) + bot (profile) + nginx (profile).

### 12.2 Railway
- `railway.toml`/`railway.json`: билд через Dockerfile target `api`.
- `start_api.sh`: запускает `create_cases_table.py`, затем `uvicorn api.main:app` (1 worker — из-за Telegram webhook lock).

### 12.3 Kubernetes
`k8s/*.yaml`:
- readiness/liveness/startup probes ожидают `/readiness`, `/liveness`, `/startup` (эти эндпоинты определены в `api/routes/health_production.py` и используются в `api/main_production.py`).

### 12.4 Локальный запуск (минимум)
Backend (вариант dev):
- `pip install -r requirements.txt`
- `uvicorn api.main:app --reload`

Backend (production-ветка API, если хотите проверить readiness/liveness):
- `uvicorn api.main_production:app --reload`

Worker:
- `python -m core.workers.task_worker start`
- `python -m core.workers.task_worker smoke`

Frontend:
- `cd web`
- `npm install`
- `npm run dev`

### 12.5 Переменные окружения (минимальный набор)
См. `.env.example` и `.env.production.example`. Практически критичное:
- JWT/безопасность: `SECURITY_JWT_SECRET_KEY` (или `JWT_SECRET_KEY` в dev-ветке).
- Telegram: `TELEGRAM_TOKEN` (или `TELEGRAM_BOT_TOKEN`) + опционально `TELEGRAM_WEBHOOK_SECRET`.
- Postgres/Supabase: `POSTGRES_DSN` (или `DATABASE_URL`), а для MCP Supabase: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
- LLM ключи (минимум один провайдер): `LLM_OPENAI_API_KEY` / `LLM_ANTHROPIC_API_KEY` / `LLM_GEMINI_API_KEY`.

## 13) Тесты и CI
- `pytest.ini`: `asyncio_mode=auto`, `testpaths=tests`.
- `.github/workflows/ci.yml`: `ruff`, `pytest`, `pip-audit`, `gitleaks`, проверка alembic файлов.
- Набор тестов структурирован по `tests/unit`, `tests/integration`, `tests/workflows`, `tests/e2e`, `tests/performance`, и др.

## 14) Безопасность и наблюдаемость
### 14.1 Security
`core/security/`:
- RBAC (`advanced_rbac.py` + загрузка политики),
- prompt injection detector,
- аудит (в т.ч. immutable audit trail),
- CORS/headers/rate limiting (в разных местах: `api/middleware.py`, `api/middleware_production.py`, `core/security/config.py`).

### 14.2 Observability
`core/observability/`:
- Prometheus метрики (`metrics_collector.py`),
- structured logging (`log_aggregation.py`),
- tracing OpenTelemetry (`distributed_tracing.py`).

## 15) Зоны риска/технического долга (по факту чтения кода)
1) Два параллельных FastAPI приложения (`api/main.py` vs `api/main_production.py`) с разными роутами/health-контрактами и настройками.
2) Несовпадение API контрактов с фронтендом: фронт ожидает `/cases`, backend имеет `.../api/v1/cases` (prod) и `/v1/case/{action}` (dev).
3) Дублирование/расхождение "settings": `config/settings.py` (AppSettings) и `core/config/production_settings.py` (другая схема, не везде используется).
4) Две версии MemoryManager + разные места выбора (DI vs `api/deps.py`).
5) Rate limiting в `api/middleware.py` — in-memory (не шарится между воркерами/инстансами); в production есть token bucket, но тоже локальный.
6) `http.get` tool зарегистрирован как stub в `api/startup.py` (для smoke/dev), что важно учитывать при ожидании "реального" network tool.
7) В `web/` присутствуют артефакты сборки/зависимостей (`node_modules`, `.next`) — утяжеляет репозиторий и анализ/CI (если не исключено).

## 16) Практические рекомендации (коротко)
- Выбрать один "канонический" entrypoint для продакшена (скорее `api/main_production.py`) и выровнять Docker/Railway/K8s под него.
- Зафиксировать публичные API контракты (cases + agui) и синхронизировать `web/src/lib/agui.ts` с backend роутами (или добавить совместимый proxy/alias).
- Консолидировать settings/memory менеджеры: один источник правды для env-переменных и один путь выбора backend-сторов.
- Для rate limiting в продакшене — вынести состояние в Redis (или ingress/gateway), иначе горизонтальное масштабирование ломает лимиты.
