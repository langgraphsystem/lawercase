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

## Monitoring & Observability
- **Prometheus**: метрики доступны на `GET /metrics` (требуется роль `admin`).
- **Structured logging**: настраивается окружением (`LOG_LEVEL`, `LOG_CONSOLE_OUTPUT`, `LOG_FILE_OUTPUT`, `LOG_JSON_FORMAT`, `LOG_DIR`). По умолчанию логируются в консоль и каталог `logs/`.
- **Distributed tracing**: опционально включается через `TRACING_ENABLED=true`. Поддерживаются экспортеры `console`, `jaeger`, `zipkin`, `otlp`. Остальные переменные: `TRACING_EXPORTER`, `TRACING_SERVICE_NAME`, `OTLP_ENDPOINT` и т.д.
- **Grafana dashboards**: сформируйте JSON при помощи `python -m core.observability.grafana_dashboards --output-dir dashboards/`, затем импортируйте файлы в Grafana.

## Security Enhancements
- **RBAC**: расширенный менеджер ролей (`core/security/advanced_rbac.py`) с поддержкой наследования и условий (MFA, IP, время, теги). Политика подключается через `RBAC_POLICY_PATH`.
- **Prompt Injection Detector**: эвристический анализ (`core/security/prompt_injection_detector.py`) применяется в команде MegaAgent. Порог настройте переменными `PROMPT_DETECTION_ENABLED` и `PROMPT_DETECTION_THRESHOLD`.
- **Immutable Audit Trail**: hash-цепочка (`core/security/audit_trail.py`) фиксирует события; путь и алгоритм управляются `AUDIT_LOG_PATH` и `AUDIT_HASH_ALGORITHM`.


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

## EB-1A Pipeline — Quickstart

### Переменные окружения

Для работы CLI и LangGraph-узлов убедитесь, что добавили в `.env` значения:

- `DOC_RAPTOR_API_KEY`
- `ADOBE_OCR_API_KEY`
- `GEMINI_API_KEY`
- `EB1A_PDF_MAX_MB`
- `TMP_DIR`, `OUT_DIR`

### Шаги запуска

```
# 1. Generate petition text PDF
python -m recommendation_pipeline.document_generator --html data/Petition.html --css data/styles.css --out out/EB1A_text.pdf

# 2. Convert exhibit images to PDF and capture metadata
python -m recommendation_pipeline.ocr_runner --images data/exhibit1/*.jpg --out out/Exhibit_1.pdf --provider gemini --analyze-only

# 3. Finalize exhibit OCR (optional)
python -m recommendation_pipeline.ocr_runner --in out/Exhibit_1.pdf --out out/Exhibit_1_ocr.pdf --provider adobe --finalize

# 4. Build exhibits index
python -m recommendation_pipeline.index_builder --in "out/Exhibit_*.pdf" --out out/exhibits_index.json

# 5. Assemble master petition PDF
python -m recommendation_pipeline.pdf_assembler --text out/EB1A_text.pdf --exhibits "out/Exhibit_*.pdf" --index out/exhibits_index.json --out out/EB1A_master.pdf

# 6. Finalize and compress master PDF as needed
python -m recommendation_pipeline.pdf_finalize --in out/EB1A_master.pdf --ocr adobe --out out/EB1A_master_OCR.pdf
```

### LangGraph интеграция

Используйте `core.orchestration.pipeline_manager.build_eb1a_pipeline(...)`, чтобы скомпилировать LangGraph workflow, построенный функцией `core.orchestration.eb1a_nodes.build_eb1a_workflow()`. Узлы импортируют и вызывают CLI-пайплайн, сохраняя результаты в `WorkflowState.agent_results["eb1a"]`.

## Telegram Bot

1. Задайте переменные окружения `TELEGRAM_BOT_TOKEN` и (опционально) `TELEGRAM_ALLOWED_USERS` (через запятую) в `.env`.
2. Запустите бота:
   ```bash
   python -m telegram_interface.bot
   ```
3. Команды:
   - `/start` — приветствие и справка.
   - `/ask <вопрос>` — запрос MegaAgent по памяти.
   - `/case_get <case_id>` — получить сведения о деле.
   - `/memory_lookup <запрос>` — поиск в семантической памяти.
   - `/generate_letter <заголовок>` — сгенерировать шаблон письма.
