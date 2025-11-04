# 🚀 Document Monitor - Quick Start Guide

## Для разработчиков: 3-минутный тест

### Шаг 1: Откройте интерфейс

```bash
# Вариант A: Прямо в браузере
start index.html

# Вариант B: Через локальный сервер (рекомендуется)
python -m http.server 8080
# Откройте http://localhost:8080/index.html
```

### Шаг 2: Включите Mock режим

1. Нажмите кнопку **"🧪 Use Mock Data"** в верхнем правом углу
2. Кнопка должна стать зеленой: **"✅ Mock Mode ON"**

### Шаг 3: Запустите генерацию

1. Нажмите большую синюю кнопку **"🚀 Начать генерацию"**
2. Наблюдайте за процессом:
   - Левая панель показывает структуру документа с обновляющимися статусами
   - Центральная панель отображает генерируемый документ
   - Правая панель показывает статистику и логи

### Шаг 4: Попробуйте функции

**Навигация:**
- Кликните на секцию в левой панели → автоматический скролл к секции в документе

**Загрузка Exhibits:**
1. Введите ID: `2.1.A`
2. Выберите любой PDF файл
3. Нажмите "Загрузить"
4. Файл появится в списке приложений

**Просмотр логов:**
- Логи обновляются в реальном времени в правой панели
- Цветовая кодировка: синий (info), зеленый (success), красный (error)

### Шаг 5: Дождитесь завершения

Через ~20 секунд:
- Все секции станут зелеными (✅ completed)
- Кнопка "📄 Скачать PDF" активируется
- Прогресс-бар достигнет 100%

---

## Для продакшена: Интеграция с backend

### Checklist интеграции

- [ ] **1. Настройте CORS на FastAPI backend**

```python
# api/main.py или api/main_production.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Ваш frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **2. Добавьте router в FastAPI**

```python
# api/main.py
from api.routes import document_monitor

app.include_router(document_monitor.router)
```

- [ ] **3. Реализуйте endpoints в `api/routes/document_monitor.py`**

Раскомментируйте TODO секции в файле:
- `start_document_generation()` - запуск workflow
- `get_document_preview()` - получение статуса
- `upload_exhibit()` - загрузка файлов
- `download_petition_pdf()` - генерация PDF

- [ ] **4. Настройте persistence layer**

Реализуйте функции для сохранения/загрузки state:

```python
async def save_workflow_state(thread_id: str, state: WorkflowState):
    # Сохранение в Redis, PostgreSQL или LangGraph checkpointer
    pass

async def load_workflow_state(thread_id: str) -> WorkflowState | None:
    # Загрузка из storage
    pass
```

- [ ] **5. Интегрируйте с LangGraph workflow**

```python
from core.orchestration.workflow_graph import build_eb1a_workflow, WorkflowState

async def run_document_generation(thread_id: str, case_id: str, user_id: str):
    # Создать initial state
    state = WorkflowState(
        thread_id=thread_id,
        case_id=case_id,
        user_id=user_id,
        workflow_step="generating",
        document_data={
            "sections": get_section_definitions("petition"),
            "exhibits": [],
            "logs": [],
            "started_at": datetime.now().isoformat(),
        }
    )

    # Сохранить
    await save_workflow_state(thread_id, state)

    # Запустить workflow
    graph = build_eb1a_workflow()

    # Option A: Sync run
    final_state = await graph.ainvoke(state, config={"thread_id": thread_id})

    # Option B: Async streaming (for real-time updates)
    async for event in graph.astream(state, thread_id=thread_id):
        updated_state = event["state"]
        await save_workflow_state(thread_id, updated_state)
```

- [ ] **6. Обновите CONFIG в index.html**

```javascript
const CONFIG = {
  API_BASE: 'http://localhost:8000/api',  // Ваш backend URL
  POLL_INTERVAL: 2000,
  MAX_POLL_ERRORS: 5,
  MOCK_MODE: false,  // Отключить mock режим
};
```

- [ ] **7. Тестируйте end-to-end**

```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
python -m http.server 8080

# Откройте http://localhost:8080/index.html
# Убедитесь что Mock Mode ВЫКЛЮЧЕН
# Нажмите "Начать генерацию"
```

---

## Распространённые проблемы

### ❌ "Failed to fetch" ошибка в консоли

**Причина**: CORS не настроен или backend не запущен

**Решение**:
1. Проверьте что backend запущен: `curl http://localhost:8000/api/health`
2. Проверьте CORS middleware в FastAPI
3. Откройте DevTools (F12) → Network tab и проверьте запросы

---

### ❌ Секции не обновляются

**Причина**: Неправильный формат response от API

**Решение**:
1. Откройте DevTools → Network → найдите запрос к `/api/document/preview/{thread_id}`
2. Проверьте Response соответствует схеме `DocumentPreviewResponse`
3. Убедитесь что `content_html` содержит валидный HTML

---

### ❌ "Thread not found" при polling

**Причина**: State не сохраняется между запросами

**Решение**:
Реализуйте persistent storage:

```python
# Вариант 1: Redis
import redis.asyncio as redis
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

async def save_workflow_state(thread_id: str, state: WorkflowState):
    await redis_client.set(
        f"workflow:{thread_id}",
        state.model_dump_json(),
        ex=86400  # 24 hours expiry
    )

async def load_workflow_state(thread_id: str) -> WorkflowState | None:
    data = await redis_client.get(f"workflow:{thread_id}")
    if data:
        return WorkflowState.model_validate_json(data)
    return None
```

```python
# Вариант 2: PostgreSQL (через SQLAlchemy)
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.ext.asyncio import AsyncSession

class WorkflowStateModel(Base):
    __tablename__ = "workflow_states"

    thread_id = Column(String, primary_key=True)
    state_json = Column(Text)
    updated_at = Column(DateTime, default=datetime.now)

async def save_workflow_state(thread_id: str, state: WorkflowState, db: AsyncSession):
    model = WorkflowStateModel(
        thread_id=thread_id,
        state_json=state.model_dump_json(),
    )
    await db.merge(model)
    await db.commit()
```

---

## Performance Tips

### 1. Оптимизируйте polling interval

```javascript
// Для production - увеличьте интервал чтобы снизить нагрузку
const CONFIG = {
  POLL_INTERVAL: 3000,  // 3 секунды вместо 2
};
```

### 2. Используйте WebSocket (опционально)

Для real-time updates без polling:

```python
# Backend (FastAPI WebSocket)
from fastapi import WebSocket

@app.websocket("/ws/document/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()

    async for event in workflow_events_stream(thread_id):
        await websocket.send_json(event)
```

```javascript
// Frontend (в index.html замените DocumentMonitor.poll())
const ws = new WebSocket(`ws://localhost:8000/ws/document/${threadId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  this.updateUI(data);
};
```

### 3. Кешируйте completed секции

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def get_section_html(section_id: str, version: int):
    # Cache generated HTML to avoid re-rendering
    pass
```

---

## Production Deployment

### Вариант 1: Serve из FastAPI static files

```python
# api/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/monitor", StaticFiles(directory=".", html=True), name="monitor")

# Доступ: http://yourserver.com/monitor/index.html
```

### Вариант 2: Отдельный Nginx frontend

```nginx
# nginx.conf
server {
    listen 80;
    server_name monitor.yourcompany.com;

    root /var/www/mega_agent_monitor;
    index index.html;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Вариант 3: Vercel/Netlify (для статики)

```bash
# Deploy static file
vercel deploy --prod

# Настройте ENV variable для API_BASE
# В index.html используйте:
const API_BASE = process.env.API_BASE || '/api';
```

---

## Security Considerations

### 1. Sanitize HTML content

```python
import bleach

ALLOWED_TAGS = ['h1', 'h2', 'h3', 'p', 'span', 'div', 'ul', 'ol', 'li', 'a']
ALLOWED_ATTRS = {'span': ['class'], 'div': ['class'], 'a': ['href', 'class']}

def sanitize_section_html(html: str) -> str:
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
```

### 2. Validate exhibit uploads

```python
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def validate_exhibit_file(file: UploadFile):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "Invalid file type")

    # Check file size (read first chunk)
    # Implementation needed
```

### 3. Rate limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/document/preview/{thread_id}")
@limiter.limit("30/minute")  # Max 30 requests per minute
async def get_document_preview(request: Request, thread_id: str):
    # ...
```

---

## Monitoring & Observability

### Add metrics

```python
from prometheus_client import Counter, Histogram

document_generations = Counter(
    'document_generations_total',
    'Total document generations started'
)

generation_duration = Histogram(
    'document_generation_duration_seconds',
    'Document generation duration'
)

@router.post("/generate-petition")
async def start_document_generation(...):
    document_generations.inc()

    with generation_duration.time():
        # ... generation logic
        pass
```

---

## Support

Вопросы? Проблемы?

1. Проверьте [DOCUMENT_MONITOR_README.md](./DOCUMENT_MONITOR_README.md) - полная документация
2. Посмотрите примеры в `api/routes/document_monitor.py`
3. Откройте DevTools (F12) в браузере для debugging

**Happy coding! 🚀**
