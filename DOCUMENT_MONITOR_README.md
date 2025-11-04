# 📊 Document Generation Monitor - Руководство разработчика

## Обзор

**index.html** - это самодостаточное одностраничное веб-приложение для мониторинга генерации юридических документов системой mega_agent_pro в реальном времени.

### Основные возможности

✅ **Real-time мониторинг** - отслеживание прогресса генерации документа через polling
✅ **Трехпанельный интерфейс** - структура документа, предпросмотр, панель управления
✅ **Mock режим** - полноценное тестирование без backend
✅ **Responsive дизайн** - адаптивность для всех экранов
✅ **Accessibility** - полная поддержка клавиатуры и screen readers
✅ **Нулевые зависимости** - чистый HTML/CSS/JavaScript

---

## 🚀 Быстрый старт

### Тестирование без backend

1. Откройте `index.html` в браузере
2. Нажмите кнопку **"🧪 Use Mock Data"** в header
3. Нажмите **"🚀 Начать генерацию"**
4. Наблюдайте за симуляцией генерации документа

Mock режим симулирует:
- Последовательную генерацию 5 секций петиции
- Прогрессивное обновление статусов (pending → in_progress → completed)
- Загрузку exhibit файлов
- Real-time логирование событий
- Обновление статистики (токены, стоимость, ETA)

### Интеграция с реальным backend

1. **Настройте API endpoints** в JavaScript (строка ~660):

```javascript
const CONFIG = {
  API_BASE: 'http://localhost:8000/api',  // Ваш FastAPI backend
  POLL_INTERVAL: 2000,                     // Интервал polling (ms)
  MAX_POLL_ERRORS: 5,                      // Макс. ошибок до остановки
  MOCK_MODE: false,                        // false для production
};
```

2. **Убедитесь что CORS настроен** на FastAPI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **Реализуйте API endpoints** (см. раздел "API Specification" ниже)

4. **Запустите систему**:

```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend (опционально, для dev server)
python -m http.server 8080
# Откройте http://localhost:8080/index.html
```

---

## 📡 API Specification

Backend должен реализовать следующие endpoints:

### 1. POST `/api/generate-petition`

**Назначение**: Запуск генерации нового документа

**Request Body**:
```json
{
  "case_id": "string",
  "document_type": "petition" | "letter" | "memo",
  "user_id": "string"
}
```

**Response**:
```json
{
  "thread_id": "string",
  "status": "generating",
  "message": "Document generation started"
}
```

---

### 2. GET `/api/document/preview/{thread_id}`

**Назначение**: Получение текущего состояния документа (для polling)

**Response** (TypeScript schema для reference):
```typescript
interface DocumentPreviewResponse {
  thread_id: string;
  status: 'idle' | 'generating' | 'paused' | 'completed' | 'error';

  sections: Array<{
    section_id: string;           // "intro", "awards", etc.
    section_name: string;          // "I. INTRODUCTION"
    section_order: number;         // 1, 2, 3...
    status: 'pending' | 'in_progress' | 'completed' | 'error';
    content_html: string;          // HTML с уже применёнными стилями
    updated_at: string;            // ISO timestamp
    tokens_used?: number;
    error_message?: string;
  }>;

  exhibits: Array<{
    exhibit_id: string;            // "2.1.A"
    filename: string;              // "Award_Certificate.pdf"
    file_path: string;             // URL для скачивания
    file_size: number;             // bytes
    mime_type: string;             // "application/pdf"
    uploaded_at: string;           // ISO timestamp
  }>;

  metadata: {
    total_sections: number;
    completed_sections: number;
    progress_percentage: number;   // 0-100
    elapsed_time: number;          // seconds
    estimated_remaining: number;   // seconds
    total_tokens: number;
    estimated_cost: number;        // USD
  };

  logs: Array<{
    timestamp: string;             // ISO timestamp
    level: 'info' | 'success' | 'error' | 'warning';
    message: string;
    agent?: string;                // "WriterAgent", "SupervisorAgent", etc.
  }>;
}
```

**Важные детали**:

- **content_html** должен содержать готовый HTML с inline стилями классов (`.bold`, `.italic`, `.center` и т.д.)
- **section_order** определяет порядок отображения секций
- Frontend автоматически обновляет только измененные секции (оптимизация)
- Polling происходит каждые 2 секунды (настраивается)

---

### 3. POST `/api/upload-exhibit/{thread_id}`

**Назначение**: Загрузка exhibit файла

**Request** (multipart/form-data):
```
exhibit_id: string (form field)
file: File (binary)
```

**Response**:
```json
{
  "success": true,
  "exhibit_id": "2.1.A",
  "filename": "Award_Certificate.pdf",
  "file_path": "/exhibits/2.1.A.pdf"
}
```

---

### 4. GET `/api/download-petition-pdf/{thread_id}`

**Назначение**: Скачивание готового PDF документа

**Response**: Binary PDF file with appropriate headers
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="petition_{thread_id}.pdf"
```

---

### 5. POST `/api/pause/{thread_id}` *(опционально)*

**Назначение**: Приостановка генерации

**Response**:
```json
{
  "status": "paused",
  "message": "Generation paused"
}
```

---

### 6. POST `/api/resume/{thread_id}` *(опционально)*

**Назначение**: Возобновление генерации

**Response**:
```json
{
  "status": "generating",
  "message": "Generation resumed"
}
```

---

## 🎨 Кастомизация

### Изменение цветовой схемы

Отредактируйте CSS variables в `:root` (строка ~140):

```css
:root {
  --color-primary: #0066cc;      /* Основной цвет */
  --color-success: #28a745;      /* Успех */
  --color-warning: #ffc107;      /* Предупреждение */
  --color-danger: #dc3545;       /* Ошибка */
  /* ... */
}
```

### Изменение интервала polling

```javascript
const CONFIG = {
  POLL_INTERVAL: 3000,  // 3 секунды вместо 2
  // ...
};
```

### Изменение стилей документа

Стили для предпросмотра документа находятся в секции `#document-preview` (строка ~435):

```css
#document-preview {
  font-family: var(--font-document);  /* Times New Roman */
  font-size: 11pt;                    /* Размер шрифта */
  line-height: 1.5;                   /* Межстрочный интервал */
  /* ... */
}
```

### Добавление новых секций в sidebar

Секции генерируются автоматически из `sections` array в API response.
Для кастомизации отображения отредактируйте `UI.updateSidebar()` (строка ~1080).

---

## 🏗️ Архитектура кода

### Основные компоненты

```
index.html
├── HTML (структура)
│   ├── Header (app-header)
│   ├── Sidebar (section/exhibit lists)
│   ├── Main Content (document preview)
│   └── Controls Panel (buttons, stats, logs)
│
├── CSS (стили)
│   ├── Variables (colors, spacing, fonts)
│   ├── Layout (grid, flexbox)
│   ├── Components (buttons, forms, cards)
│   ├── Document styles (Times New Roman, formatting)
│   └── Responsive (media queries)
│
└── JavaScript (логика)
    ├── CONFIG (конфигурация)
    ├── API_ENDPOINTS (маршруты)
    ├── MOCK_DATA (тестовые данные)
    ├── DocumentMonitor (класс для polling)
    ├── UI (методы обновления интерфейса)
    └── Event Handlers (кнопки, формы)
```

### Класс DocumentMonitor

```javascript
class DocumentMonitor {
  constructor(threadId, options)
  async startPolling()           // Запуск мониторинга
  async poll()                   // Один цикл polling
  async fetchStatus()            // Запрос к API
  async getMockData()            // Генерация mock данных
  updateUI(data)                 // Обновление всего UI
  stopPolling()                  // Остановка мониторинга
  onComplete(data)               // Обработчик завершения
  onError(data)                  // Обработчик ошибки
}
```

### Объект UI

Централизованное управление обновлением интерфейса:

```javascript
const UI = {
  updateSidebar(sections, exhibits)    // Обновление левой панели
  updateMainContent(sections)          // Обновление документа
  updateStatistics(metadata)           // Обновление статистики
  updateLogs(logs)                     // Добавление логов
  addLog(level, message, agent)        // Добавление одного лога
  updateControlButtons(status)         // Обновление кнопок

  // Utility методы
  scrollToSection(sectionId)
  getStatusIcon(status)
  getFileIcon(mimeType)
  formatFileSize(bytes)
  formatDuration(seconds)
  formatTimeAgo(timestamp)
  showNotification(message, type)
}
```

---

## 🔧 Backend Implementation Example

### FastAPI endpoint для `/api/document/preview/{thread_id}`

```python
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Literal
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api", tags=["document"])

# Schemas
class Section(BaseModel):
    section_id: str
    section_name: str
    section_order: int
    status: Literal["pending", "in_progress", "completed", "error"]
    content_html: str
    updated_at: datetime
    tokens_used: int | None = None
    error_message: str | None = None

class Exhibit(BaseModel):
    exhibit_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_at: datetime

class Metadata(BaseModel):
    total_sections: int
    completed_sections: int
    progress_percentage: float
    elapsed_time: int
    estimated_remaining: int
    total_tokens: int
    estimated_cost: float

class Log(BaseModel):
    timestamp: datetime
    level: Literal["info", "success", "error", "warning"]
    message: str
    agent: str | None = None

class DocumentPreviewResponse(BaseModel):
    thread_id: str
    status: Literal["idle", "generating", "paused", "completed", "error"]
    sections: List[Section]
    exhibits: List[Exhibit]
    metadata: Metadata
    logs: List[Log]

# Endpoint
@router.get("/document/preview/{thread_id}", response_model=DocumentPreviewResponse)
async def get_document_preview(thread_id: str):
    """Get current status of document generation."""

    # TODO: Получить состояние из вашего workflow state
    # Например, через LangGraph checkpointer или database

    workflow_state = await get_workflow_state(thread_id)

    if not workflow_state:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Конвертация вашего WorkflowState в DocumentPreviewResponse
    return DocumentPreviewResponse(
        thread_id=thread_id,
        status=workflow_state.workflow_step,
        sections=[
            Section(
                section_id=sec.id,
                section_name=sec.name,
                section_order=sec.order,
                status=sec.status,
                content_html=sec.html_content,
                updated_at=sec.updated_at,
                tokens_used=sec.tokens,
            )
            for sec in workflow_state.sections
        ],
        exhibits=workflow_state.exhibits,
        metadata=calculate_metadata(workflow_state),
        logs=workflow_state.logs[-50:],  # Last 50 logs
    )

async def get_workflow_state(thread_id: str):
    """Retrieve workflow state from checkpointer or database."""
    # Ваша реализация - например:
    # return await memory_manager.get_state(thread_id)
    pass

def calculate_metadata(state) -> Metadata:
    """Calculate metadata from workflow state."""
    completed = sum(1 for s in state.sections if s.status == "completed")
    total = len(state.sections)

    return Metadata(
        total_sections=total,
        completed_sections=completed,
        progress_percentage=(completed / total * 100) if total > 0 else 0,
        elapsed_time=int((datetime.now() - state.started_at).total_seconds()),
        estimated_remaining=estimate_remaining_time(state),
        total_tokens=sum(s.tokens or 0 for s in state.sections),
        estimated_cost=calculate_cost(state),
    )
```

### Интеграция с LangGraph workflow

```python
from langgraph.graph import StateGraph
from core.orchestration.workflow_graph import WorkflowState

async def document_generation_workflow(
    case_id: str,
    thread_id: str,
    user_id: str
) -> None:
    """Run document generation workflow with state updates."""

    # Создать workflow state
    state = WorkflowState(
        thread_id=thread_id,
        user_id=user_id,
        case_id=case_id,
        workflow_step="generating",
        document_data={
            "sections": [
                {"id": "intro", "name": "I. INTRODUCTION", "order": 1, "status": "pending"},
                {"id": "background", "name": "II. BACKGROUND", "order": 2, "status": "pending"},
                # ... остальные секции
            ],
            "exhibits": [],
            "logs": [],
        }
    )

    # Сохранить начальное состояние
    await save_state(thread_id, state)

    # Запустить LangGraph workflow
    graph = build_eb1a_workflow()

    async for event in graph.astream(state, thread_id=thread_id):
        # После каждого узла обновляем state
        updated_state = event["state"]
        await save_state(thread_id, updated_state)

        # Логирование
        await log_event(thread_id, {
            "timestamp": datetime.now(),
            "level": "info",
            "message": f"Completed node: {event['node']}",
            "agent": event.get("agent_name"),
        })
```

---

## 🎯 Best Practices

### 1. Оптимизация производительности

**Throttle/Debounce для частых обновлений**:

```javascript
// Добавьте перед updateUI в DocumentMonitor
let updateTimeout;
updateUI(data) {
  clearTimeout(updateTimeout);
  updateTimeout = setTimeout(() => {
    UI.updateSidebar(data.sections, data.exhibits);
    UI.updateMainContent(data.sections);
    UI.updateStatistics(data.metadata);
    UI.updateLogs(data.logs);
    UI.updateControlButtons(data.status);
  }, 100); // Debounce 100ms
}
```

**Lazy rendering для длинных документов**:

```javascript
// Используйте Intersection Observer для lazy load секций
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      // Render section content
      renderSection(entry.target.dataset.sectionId);
    }
  });
});
```

### 2. Обработка ошибок

**Graceful degradation**:

```javascript
async poll() {
  try {
    const data = await this.fetchStatus();
    // ...
  } catch (error) {
    // Не ломаем весь UI, показываем user-friendly сообщение
    if (error.message.includes('NetworkError')) {
      UI.addLog('warning', 'Временные проблемы с сетью, повторяю...', 'System');
    } else {
      UI.addLog('error', 'Ошибка получения данных', 'System');
    }
  }
}
```

### 3. Accessibility

**Keyboard navigation**:

Все интерактивные элементы уже имеют:
- `tabindex` для фокуса
- Event handlers для `Enter` и `Space`
- ARIA labels для иконок

**Screen reader support**:

```html
<span class="status-icon" aria-label="Section completed">✅</span>
```

### 4. Security

**Sanitize HTML content**:

ВАЖНО: Backend должен санитизировать `content_html` перед отправкой!

```python
import bleach

ALLOWED_TAGS = ['h1', 'h2', 'h3', 'p', 'span', 'div', 'ul', 'ol', 'li', 'a']
ALLOWED_ATTRIBUTES = {'span': ['class'], 'div': ['class'], 'a': ['href', 'class']}

def sanitize_html(html: str) -> str:
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
```

---

## 🐛 Troubleshooting

### Проблема: Polling не работает

**Причина**: CORS или неправильный API_BASE

**Решение**:
1. Откройте DevTools (F12) → Network tab
2. Проверьте запросы к API
3. Если видите CORS ошибки, настройте backend (см. выше)
4. Убедитесь что `API_BASE` указывает на правильный URL

### Проблема: Секции не отображаются

**Причина**: Неправильный формат `content_html`

**Решение**:
1. Откройте DevTools → Console
2. Проверьте вывод `console.log` в `updateMainContent`
3. Убедитесь что `content_html` содержит валидный HTML
4. Проверьте что классы стилей применены (`.bold`, `.center` и т.д.)

### Проблема: Mock данные не обновляются

**Причина**: Логика симуляции в `getMockData()` статична

**Решение**:
Измените логику в `getMockData()` для более динамичной симуляции:

```javascript
async getMockData() {
  const elapsed = Math.floor((Date.now() - this.startTime) / 1000);

  // Каждые 5 секунд завершать одну секцию
  const completedCount = Math.min(
    Math.floor(elapsed / 5),
    MOCK_DATA.sections.length
  );

  MOCK_DATA.sections.forEach((section, idx) => {
    if (idx < completedCount) {
      section.status = 'completed';
      section.content_html = `<h2>${section.section_name}</h2><p>Content...</p>`;
    } else if (idx === completedCount) {
      section.status = 'in_progress';
    } else {
      section.status = 'pending';
    }
  });

  return MOCK_DATA;
}
```

---

## 📚 Дополнительные ресурсы

### Связанные файлы проекта

- `core/orchestration/workflow_graph.py` - LangGraph workflow definitions
- `core/groupagents/writer_agent.py` - WriterAgent implementation
- `core/workflows/eb1a/templates/section_templates.py` - Section templates
- `api/routes/agent.py` - Existing API routes
- `api/schemas.py` - Pydantic schemas

### Референсы

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [CSS Grid Layout](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout)

---

## 🔮 Roadmap (Будущие улучшения)

### Phase 2 Features

- [ ] **WebSocket support** - переход от polling к real-time updates
- [ ] **Human-in-the-loop UI** - modal dialogs для approval/rejection
- [ ] **Version comparison** - сравнение версий документа при re-generation
- [ ] **Inline comments** - комментарии ValidatorAgent прямо в документе
- [ ] **Export logs** - скачивание логов в текстовый файл
- [ ] **Search in document** - Ctrl+F enhancement с highlighting
- [ ] **Multiple document tabs** - параллельный мониторинг нескольких документов

### Phase 3 Features

- [ ] **Collaborative editing** - несколько пользователей в real-time
- [ ] **Analytics dashboard** - статистика по всем генерациям
- [ ] **Template library** - библиотека шаблонов документов
- [ ] **AI suggestions** - inline AI-powered improvements
- [ ] **Offline mode** - Service Worker для работы без сети

---

## 📄 License

Этот компонент является частью проекта **mega_agent_pro**.
См. LICENSE файл в корне проекта.

---

## 🤝 Contributing

При добавлении новых features:

1. Сохраняйте zero-dependency принцип (только vanilla JS)
2. Следуйте существующему code style
3. Добавляйте комментарии для сложной логики
4. Тестируйте в mock режиме перед интеграцией
5. Обновляйте этот README

---

## 📞 Support

Для вопросов и bug reports:
- GitHub Issues: [mega_agent_pro/issues](https://github.com/yourusername/mega_agent_pro/issues)
- Email: support@megaagentpro.com

---

**Создано с ❤️ для mega_agent_pro project**
