# Точки входа пользователя в систему MegaAgent EB-1A

## Обзор

Система MegaAgent EB-1A предоставляет несколько точек входа для взаимодействия пользователей с платформой. Этот документ описывает все способы начала работы с системой.

---

## 1. Web-интерфейс (Next.js Frontend)

**URL продакшен:** https://eb1a-frontend.vercel.app/

### 1.1 Первичная аутентификация

**Эндпоинт:** `POST /auth/login`

Пользователь начинает работу с аутентификации через форму логина:

```typescript
// Пример запроса
POST https://refreshing-reprieve-production-9802.up.railway.app/auth/login
Content-Type: application/json

{
  "email": "client@eb1a.com",
  "password": "demo1234"
}
```

**Демо-пользователи (для MVP):**
- `admin@eb1a.com` - роль: `admin`
- `lawyer@eb1a.com` - роль: `lawyer`
- `client@eb1a.com` - роль: `viewer`
- Пароль по умолчанию: `demo1234` (конфигурируется через `DEMO_USER_PASSWORD`)

**Ответ:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user_id": "client-001",
  "roles": ["viewer"]
}
```

JWT токен действует 24 часа (настраивается через `JWT_EXPIRE_HOURS`).

### 1.2 Главная страница чата

**Путь:** `/chat` (web/src/app/chat/page.tsx)

После аутентификации пользователь попадает на страницу чата, где может:

1. **Выбрать существующий кейс** из списка
2. **Создать новый кейс** (если есть права)
3. **Задать вопрос системе** через чат-интерфейс

**Основные действия:**

#### a) Получение списка кейсов
```http
GET /cases
Authorization: Bearer <jwt_token>
```

#### b) Создание нового кейса
```http
POST /api/v1/cases
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "applicant_name": "John Doe",
  "field": "Machine Learning",
  "status": "intake"
}
```

#### c) Отправка вопроса через AG-UI протокол
```http
POST /agui/run
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "prompt": "Проанализируй мои шансы на EB-1A",
  "case_id": "case-123",
  "stream": true
}
```

Ответ приходит через Server-Sent Events (SSE) с событиями:
- `RUN_START` - начало обработки
- `TEXT_CHUNK` - фрагменты текста ответа
- `STEP_START/STEP_END` - шаги обработки
- `RUN_COMPLETE` - завершение

---

## 2. Telegram Bot

**Включение:** Установить `TELEGRAM_BOT_TOKEN` в `.env`

### 2.1 Команда /start

Первое взаимодействие пользователя с ботом:

```
/start
```

**Ответ бота:**
```
👋 Welcome to MegaAgent EB-1A assistant! Use /help to see available commands.
```

### 2.2 Основные команды для нового пользователя

#### a) Просмотр справки
```
/help
```

Показывает полный список доступных команд (см. раздел 2.4).

#### b) Создание нового кейса
```
/case_create
```

Запускает интерактивный диалог для создания кейса.

#### c) Начало анкетирования
```
/intake_start
```

Запускает пошаговое анкетирование для сбора информации о кандидате. Это **рекомендуемый первый шаг** для нового пользователя.

**Процесс анкетирования включает блоки:**
1. **Основная информация** - имя, дата рождения, гражданство
2. **Образование** - степени, учебные заведения
3. **Карьера** - текущая позиция, компании
4. **Достижения** - публикации, награды, патенты
5. **Членство** - профессиональные организации
6. **Критическая роль** - судейство, рецензирование
7. **Медиа** - упоминания в прессе
8. **Коммерческий успех** - доход от работы

**Навигация:**
- Ответы вводятся текстом в чат
- Inline-кнопки для навигации: "⏭ Пропустить", "⏸ Пауза", "🔙 Назад"
- Прогресс сохраняется в БД, можно продолжить позже

#### d) Быстрая оценка потенциала
```
/eb1_potential
```

Для пользователей, которые хотят быстро оценить свои шансы без полного анкетирования.

### 2.3 Авторизация Telegram пользователей

Доступ контролируется через `TELEGRAM_ALLOWED_USERS` (список Telegram user ID через запятую):

```env
TELEGRAM_ALLOWED_USERS=123456789,987654321
```

Если переменная не установлена - доступ открыт для всех.

### 2.4 Полный список команд

**🗂️ Управление кейсами:**
- `/case_create` - Создать новый кейс
- `/case_get` - Открыть кейс по ID
- `/case_list` - Список всех кейсов
- `/case_active` - Показать активный кейс
- `/case_update` - Редактировать кейс
- `/case_delete` - Удалить кейс
- `/case_archive` - Архивировать кейс

**📝 Анкетирование:**
- `/intake_start` - Начать анкетирование ⭐ **РЕКОМЕНДУЕМОЕ ПЕРВОЕ ДЕЙСТВИЕ**
- `/intake_status` - Прогресс анкеты
- `/intake_resume` - Продолжить с паузы
- `/intake_cancel` - Отменить анкету

**📊 EB-1A Анализ:**
- `/eb1_potential` - Быстрая оценка потенциала
- `/eb1_analyze` - Полный анализ критериев

**🔍 Поиск и память:**
- `/ask` - Спросить MegaAgent
- `/kb_search` - Поиск в базе знаний
- `/memory_search` - Поиск по всей памяти
- `/kb_stats` - Статистика базы знаний
- `/memory_stats` - Полная статистика памяти

**📄 Документы:**
- `/generate_letter` - Сгенерировать письмо
- Отправка PDF файла - автоматическая загрузка документа

**🔌 MCP Инструменты:**
- `/mcp_status` - Статус MCP серверов
- `/mcp_connect` - Подключиться к MCP
- `/mcp_tools` - Список доступных инструментов
- `/mcp_query` - Запрос через MCP агента
- `/mcp_disconnect` - Отключиться от MCP

**⚙️ Система:**
- `/menu` - Главное меню
- `/status` - Статус системы
- `/cancel` - Отменить текущее действие
- `/help` - Справка

---

## 3. REST API (прямое использование)

Для разработчиков и интеграций.

**Backend URL:** https://refreshing-reprieve-production-9802.up.railway.app

### 3.1 Аутентификация

```http
POST /auth/login
Content-Type: application/json

{
  "email": "lawyer@eb1a.com",
  "password": "demo1234"
}
```

### 3.2 Основные эндпоинты

**Health Check:**
```http
GET /health
GET /ready
```

**Запрос к агенту:**
```http
POST /v1/ask
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "Какие критерии EB-1A?"
}
```

**Поиск в памяти:**
```http
POST /v1/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "patent applications",
  "top_k": 5
}
```

**Вызов инструмента:**
```http
POST /v1/tool
Authorization: Bearer <token>
Content-Type: application/json

{
  "tool_id": "http.get",
  "arguments": {"url": "https://example.com"},
  "network": true
}
```

**Управление кейсами:**
```http
POST /v1/case/create
POST /v1/case/get
POST /v1/case/update
POST /v1/case/delete
```

---

## 4. Workflow интеграция (LangGraph)

Для автоматизированных процессов и интеграций.

### 4.1 Запуск полного EB-1A пайплайна

```python
from core.orchestration.pipeline_manager import build_eb1a_pipeline

pipeline = build_eb1a_pipeline(memory_manager, llm_router)
result = await pipeline.ainvoke({
    "case_id": "case-123",
    "applicant_name": "John Doe",
    "field": "AI Research"
})
```

### 4.2 Основные этапы workflow

1. **Eligibility Check** - первичная проверка соответствия
2. **Evidence Collection** - сбор документов
3. **Criteria Assessment** - анализ по 10 критериям EB-1A
4. **Strength Analysis** - оценка силы кейса
5. **Gap Analysis** - выявление недостающих элементов
6. **Document Generation** - генерация петиции и писем
7. **Validation** - проверка качества
8. **Human Review** - передача юристу
9. **Finalization** - финализация пакета

---

## 5. Рекомендуемый путь для нового пользователя

### Вариант A: Через Telegram (наиболее простой)

1. Найти бота в Telegram
2. Отправить `/start`
3. Отправить `/intake_start` ⭐
4. Пройти анкетирование (8 блоков вопросов)
5. Получить `/eb1_analyze` - анализ шансов
6. Запросить `/generate_letter` для рекомендательных писем

### Вариант B: Через Web-интерфейс

1. Перейти на https://eb1a-frontend.vercel.app/
2. Войти через форму логина (email + password)
3. Создать новый кейс
4. Задать вопросы в чате для первичной оценки
5. Загрузить документы через интерфейс
6. Отслеживать прогресс через дашборд

### Вариант C: API интеграция

1. Получить JWT токен через `/auth/login`
2. Создать кейс через `POST /api/v1/cases`
3. Запустить анкетирование через API
4. Получить анализ через `/v1/ask` или прямой вызов workflow

---

## 6. Хранение данных и сессии

### 6.1 Web-интерфейс
- История чата хранится в `localStorage` браузера (per case)
- JWT токен в памяти сессии
- Состояние кейса синхронизируется с backend

### 6.2 Telegram
- Прогресс анкетирования в Postgres/Supabase (`intake_progress` table)
- Контекст разговора в Telegram context
- Все факты из анкеты сохраняются в семантической памяти

### 6.3 Backend
- **Supabase/PostgreSQL** - основное хранилище (кейсы, память, документы)
- **Redis** - кэширование и сессии
- **Semantic Memory** - pgvector для поиска по смыслу
- **Episodic Memory** - история взаимодействий
- **Working Memory** - текущий контекст агента

---

## 7. Rate Limits и ограничения

**По умолчанию:**
- API: 60 запросов/минуту на IP (настраивается через `API_RATE_LIMIT`, `API_RATE_WINDOW`)
- Telegram: без явных ограничений (контролируется Telegram API)
- AG-UI streaming: время ожидания ответа до 300 секунд

**Роли и доступ:**
- `admin` - полный доступ ко всем функциям включая `/metrics`
- `lawyer` - доступ к кейсам, инструментам, анализу
- `viewer` - только чтение и базовые запросы

---

## 8. Troubleshooting

### Проблема: "Access denied" в Telegram
**Решение:** Добавить ваш Telegram user ID в `TELEGRAM_ALLOWED_USERS`

### Проблема: "401 Unauthorized" в API
**Решение:**
1. Проверить валидность JWT токена
2. Убедиться, что токен не истёк (24 часа)
3. Обновить токен через `/auth/login`

### Проблема: "503 Service Unavailable"
**Решение:** Проверить статус backend через `/health` и `/ready`

### Проблема: Frontend не может подключиться к API
**Решение:** Проверить `NEXT_PUBLIC_API_URL` в web/.env

---

## 9. Дополнительная документация

- [PROJECT_ANALYSIS.md](./PROJECT_ANALYSIS.md) - полная архитектура системы
- [AGENTS.md](../AGENTS.md) - описание агентов
- [README.md](../README.md) - установка и настройка
- [API Documentation](../api/README.md) - детальное описание API

---

## 10. Контакты и поддержка

- **GitHub Backend:** https://github.com/langgraphsystem/lawercase
- **GitHub Frontend:** https://github.com/langgraphsystem/eb1a-frontend
- **Branch:** `hardening/roadmap-v1`

Для вопросов по интеграции создавайте issues в соответствующем репозитории.
