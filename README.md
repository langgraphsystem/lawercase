# Реализация LangGraph/LangChain для mega_agent_pro

Этот пакет добавляет минимальный рабочий пайплайн на базе LangGraph, интегрированный с существующим `MemoryManager` (эпизодическая/семантическая память и RMT буфер).

## Что добавлено
- `core/orchestration/workflow_graph.py` — узлы графа: логирование события → рефлексия фактов → поиск релевантной памяти → обновление RMT слотов.
- `core/orchestration/pipeline_manager.py` — сборка/компиляция графа и запуск с чекпоинтером (in‑memory/SQLite).
- `app_demo.py` — простой асинхронный демо-сценарий запуска пайплайна.
- `requirements.txt` — зависимости (LangGraph/LangChain/Pydantic v2).

## Установка
1. Python 3.11+
2. Установите зависимости:
   - `pip install -r requirements.txt`

## Запуск демо
- `python app_demo.py`

Скрипт создаёт `AuditEvent`, прогоняет его через граф, отражает факт в семантической памяти, делает упрощённый поиск и обновляет RMT буфер. В консоли увидите отражённые факты, найденные записи и сформированные слоты RMT.

## FastAPI слой
- Приложение: `uvicorn api.main:app --reload`.
- Авторизация: Bearer JWT (секреты задаются через `.env` или `env/*.env`).
- Основные эндпоинты:
  - `GET /health`, `GET /ready`
  - `GET /metrics` (только для ролей с `admin`)
  - `POST /v1/ask`, `/v1/search`, `/v1/tool`, `/v1/agent/command`
  - `POST /v1/case/{action}` — операции над делами
  - `/v1/memory/snapshot|write|retrieve`
- Ограничение запросов по умолчанию: 60 запросов/минуту (см. `API_RATE_LIMIT`, `API_RATE_WINDOW`).
- Встроенный инструмент `http.get` (доступен для ролей `admin`, `lawyer`):
  ```json
  POST /v1/tool
  {
    "tool_id": "http.get",
    "arguments": {"url": "https://example.com"},
    "network": true
  }
  ```

## Как расширять
- Добавить новые узлы (например, RAG генерацию ответа через LangChain LLM) в `workflow_graph.py` и связать рёбрами.
- Подключить постоянное хранилище (pgvector/FAISS/Redis) вместо in‑memory стораджей, не меняя интерфейсы `SemanticStore`/`EpisodicStore`/`WorkingMemory`.
- Вставить реальный `Embedder` (через LangChain или собственный клиент) и передать в `MemoryManager`.
- В `pipeline_manager.setup_checkpointer` указать `sqlite:///file.db` для сохранения прогресса графа.

## Примечания
- Текущая реализация фокусируется на интеграции с памятью и оркестрацией. Полный функционал из `codex_spec.json` можно наращивать пошагово: добавить `MegaAgent`, специализированных агентов, RAG‑индексацию, роутинг LLM и пр.

## Docker Compose
- `docker-compose.yml` поднимает Redis и PostgreSQL, а также dev‑экземпляр API (uvicorn с `--reload`).
- Профили окружения: `env/dev.env`, `env/prod.env`.
- Запуск: `docker-compose up --build`. Перед продакшеном заполните `.env`/`env/prod.env` реальными ключами и настроите `USE_PROD_MEMORY=true`.
