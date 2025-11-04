# Railway Deployment Guide for MegaAgent Pro

Полное руководство по развертыванию MegaAgent Pro на платформе Railway.

## Содержание

1. [Подготовка](#подготовка)
2. [Создание проекта на Railway](#создание-проекта-на-railway)
3. [Настройка переменных окружения](#настройка-переменных-окружения)
4. [Развертывание сервисов](#развертывание-сервисов)
5. [Проверка работоспособности](#проверка-работоспособности)
6. [Мониторинг и логи](#мониторинг-и-логи)
7. [Решение проблем](#решение-проблем)

---

## Подготовка

### 1. Требования

- Аккаунт на [Railway.app](https://railway.app)
- GitHub аккаунт с доступом к репозиторию
- Готовые API ключи для сервисов

### 2. Проверьте конфигурацию

Убедитесь, что в репозитории присутствуют:

```bash
✓ Dockerfile               # Multi-stage build с target 'api', 'bot', 'worker'
✓ railway.json             # Конфигурация Railway
✓ railway.toml             # Альтернативный формат конфигурации
✓ start_api.sh             # Скрипт запуска с динамическим PORT
✓ .dockerignore            # Исключения для Docker build
✓ requirements.txt         # Python зависимости
```

---

## Создание проекта на Railway

### Вариант 1: Через Railway Dashboard

1. Войдите на [Railway.app](https://railway.app)
2. Нажмите **"New Project"**
3. Выберите **"Deploy from GitHub repo"**
4. Выберите репозиторий `mega_agent_pro_codex_handoff`
5. Railway автоматически обнаружит `Dockerfile` и `railway.json`

### Вариант 2: Через Railway CLI

```bash
# Установите Railway CLI
npm i -g @railway/cli

# Войдите в аккаунт
railway login

# Инициализируйте проект
railway init

# Подключите к GitHub
railway link
```

---

## Настройка переменных окружения

### Обязательные переменные для API сервиса

В Railway Dashboard → Your Project → Variables, добавьте:

#### Database (PostgreSQL)
```bash
POSTGRES_DSN=postgresql+asyncpg://user:password@host:5432/database  # pragma: allowlist secret
DATABASE_URL=postgresql://user:password@host:5432/database  # pragma: allowlist secret
PG_DSN=postgresql://user:password@host:5432/database  # pragma: allowlist secret
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

#### LLM API Keys
```bash
OPENAI_API_KEY=sk-proj-your-openai-key-here
GEMINI_API_KEY=your-gemini-api-key-here
LLM_OPENAI_API_KEY=sk-proj-your-openai-key-here
LLM_GEMINI_API_KEY=your-gemini-api-key-here
```

#### Vector Store (Pinecone)
```bash
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=mega-agent-semantic
```

#### Embeddings (Voyage AI)
```bash
VOYAGE_API_KEY=your-voyage-api-key
VOYAGE_MODEL=voyage-3-large
VOYAGE_DIMENSION=2048
```

#### Storage (Cloudflare R2)
```bash
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=mega-agent-documents
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
```

#### Security
```bash
JWT_SECRET_KEY=your-strong-secret-key-at-least-32-characters-long
SECURITY_JWT_SECRET_KEY=your-strong-secret-key-at-least-32-characters-long
```

#### Application Settings
```bash
ENV=production
PYTHONUNBUFFERED=1
USE_PROD_MEMORY=false
API_RATE_LIMIT=60
API_RATE_WINDOW=60
```

#### Observability
```bash
TRACING_ENABLED=false
TRACING_EXPORTER=console
TRACING_SERVICE_NAME=megaagent-pro
LOG_SERVICE_NAME=megaagent-pro
LOG_LEVEL=INFO
LOG_CONSOLE_OUTPUT=true
LOG_FILE_OUTPUT=false
LOG_JSON_FORMAT=true
```

### Переменные для Telegram Bot сервиса

```bash
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_ALLOWED_USERS=comma,separated,user,ids
```

**ВАЖНО**: Railway автоматически устанавливает переменную `PORT` - не переопределяйте её!

---

## Развертывание сервисов

Railway поддерживает мульти-сервисную архитектуру. Для MegaAgent Pro нужны:

### 1. PostgreSQL Database

```bash
# В Railway Dashboard
1. New → Database → Add PostgreSQL
2. Railway создаст базу и переменные: DATABASE_URL, PGHOST, PGPORT, etc.
3. Скопируйте CONNECTION_STRING и используйте для POSTGRES_DSN
```

### 2. Redis Cache (опционально)

```bash
# В Railway Dashboard
1. New → Database → Add Redis
2. Используйте REDIS_URL для подключения
```

### 3. API Service (основной)

```bash
# Railway автоматически:
1. Обнаружит Dockerfile
2. Использует build target 'api' из railway.json
3. Запустит start_api.sh с динамическим $PORT
4. Создаст публичный URL: https://your-app.railway.app
```

**Настройки:**
- Build Command: автоматически (Docker)
- Start Command: `/bin/bash start_api.sh` (из railway.json)
- Health Check: `/health` endpoint
- Port: автоматически из $PORT

### 4. Telegram Bot Service (опционально)

Для бота создайте отдельный сервис:

```bash
# В Settings → Build:
Docker Build Target: bot

# В Settings → Deploy:
Start Command: python -m telegram_interface.bot
```

---

## Проверка работоспособности

### 1. Проверьте логи развертывания

```bash
# Через Railway CLI
railway logs

# Или в Dashboard → Deployments → View Logs
```

Ожидаемый вывод:
```
Building with Dockerfile...
[+] Building API stage...
Starting MegaAgent Pro API on port 8080 with 4 workers...
INFO: Started server process
INFO: Waiting for application startup.
INFO: Application startup complete.
```

### 2. Проверьте health endpoint

```bash
curl https://your-app.railway.app/health

# Ожидаемый ответ:
{
  "status": "healthy",
  "environment": "production",
  "version": "1.0.0"
}
```

### 3. Проверьте API документацию

**ВАЖНО**: В production режиме документация отключена по умолчанию.

Чтобы включить:
```bash
# Установите переменную
ENV=development

# Или измените в core/config/production_settings.py
```

Доступ:
- OpenAPI: `https://your-app.railway.app/openapi.json`
- Swagger UI: `https://your-app.railway.app/docs`
- ReDoc: `https://your-app.railway.app/redoc`

### 4. Тестовый запрос к API

```bash
curl -X POST https://your-app.railway.app/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello, how are you?"}'
```

---

## Мониторинг и логи

### Метрики Railway

Railway предоставляет:
- CPU Usage
- Memory Usage
- Network Traffic
- Deployment History
- Build Times

Доступ: Dashboard → Your Service → Metrics

### Логи приложения

```bash
# Реалтайм логи
railway logs --follow

# Последние 100 строк
railway logs --tail 100

# Фильтр по сервису
railway logs --service api
```

### Health Checks

Railway автоматически проверяет:
- HTTP endpoint: `GET /health`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

### Observability (опционально)

Для продвинутого мониторинга:

```bash
# Включите трейсинг
TRACING_ENABLED=true
TRACING_EXPORTER=otlp
OTLP_ENDPOINT=your-collector-endpoint:4317
```

Интеграция с:
- Jaeger
- Zipkin
- Prometheus
- Grafana

---

## Решение проблем

### Проблема 1: Build Failed

**Симптомы:**
```
ERROR: failed to solve: failed to read dockerfile
```

**Решение:**
```bash
# Проверьте наличие Dockerfile в корне
ls -la Dockerfile

# Проверьте railway.json
cat railway.json

# Убедитесь что buildTarget указан правильно
"buildTarget": "api"
```

### Проблема 2: Port Binding Error

**Симптомы:**
```
ERROR: [Errno 98] Address already in use
```

**Решение:**
- Railway передает порт через переменную `$PORT`
- Убедитесь что `start_api.sh` использует `${PORT:-8000}`
- НЕ устанавливайте PORT вручную в переменных окружения

### Проблема 3: Database Connection Failed

**Симптомы:**
```
asyncpg.exceptions.InvalidCatalogNameError: database "railway" does not exist
```

**Решение:**
```bash
# Проверьте переменные базы данных
railway variables

# Убедитесь что POSTGRES_DSN совпадает с DATABASE_URL от Railway
# Формат: postgresql+asyncpg://user:pass@host:port/dbname  # pragma: allowlist secret
```

### Проблема 4: API Key Errors (401/403)

**Симптомы:**
```
OpenAI API Error: 401 Incorrect API key
```

**Решение:**
```bash
# Проверьте что все API ключи установлены
railway variables | grep API_KEY

# Убедитесь что нет лишних пробелов или кавычек
# Railway автоматически экранирует значения

# Пересоздайте ключи если необходимо
```

### Проблема 5: Медленный Build

**Оптимизация:**

1. Используйте .dockerignore:
```bash
# Исключите ненужные файлы
tests/
docs/
*.md
.git/
```

2. Multi-stage build уже настроен в Dockerfile
3. Railway кеширует слои Docker

### Проблема 6: Memory Limit

**Симптомы:**
```
Process killed (OOM - Out of Memory)
```

**Решение:**

```bash
# Уменьшите workers в start_api.sh
WORKERS=2  # вместо 4

# Или увеличьте план Railway:
# Hobby: 512MB RAM (бесплатно, ограничено)
# Pro: 8GB RAM
```

### Проблема 7: Telegram Bot не отвечает

**Проверьте:**

```bash
# 1. Логи бота
railway logs --service bot

# 2. Webhook конфликты (если использовали раньше)
curl https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook

# 3. Переменные окружения
railway variables --service bot | grep TELEGRAM
```

---

## Автоматическое развертывание (CI/CD)

Railway автоматически деплоит при push в GitHub:

### Настройка

1. Railway Dashboard → Settings → Deployments
2. Включите "Auto Deploy"
3. Выберите ветку (обычно `main` или `production`)

### Триггеры деплоя

- Push в выбранную ветку
- Merge pull request
- Manual deploy в Dashboard

### Откат версии

```bash
# Через CLI
railway rollback

# Или в Dashboard → Deployments → Previous → Rollback
```

---

## Масштабирование

### Горизонтальное масштабирование

Railway Pro план поддерживает:
- Multiple instances (replicas)
- Load balancing
- Auto-scaling

### Вертикальное масштабирование

```bash
# Увеличьте workers в start_api.sh
WORKERS=${WORKERS:-8}  # вместо 4

# Или через переменную окружения
WORKERS=8
```

---

## Стоимость на Railway

### Hobby Plan (Free)
- 512MB RAM
- Shared CPU
- 5GB bandwidth/month
- $5 credit/month

### Pro Plan ($20/month)
- 8GB RAM
- Dedicated vCPU
- 100GB bandwidth
- Unlimited projects

### Enterprise
- Custom resources
- SLA
- Priority support

---

## Дополнительные ресурсы

- [Railway Documentation](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [Railway Templates](https://railway.app/templates)
- [Railway Blog](https://blog.railway.app)

---

## Чеклист развертывания

Перед финальным деплоем проверьте:

- [ ] Все API ключи установлены
- [ ] PostgreSQL база создана и подключена
- [ ] `start_api.sh` имеет права на выполнение
- [ ] `.dockerignore` исключает ненужные файлы
- [ ] Health check endpoint работает
- [ ] Логи показывают успешный старт
- [ ] Тестовый запрос возвращает корректный ответ
- [ ] Environment переменные без лишних пробелов
- [ ] JWT_SECRET_KEY установлен (min 32 chars)
- [ ] Telegram bot token корректен (если используется)

---

## Поддержка

При проблемах:

1. Проверьте логи: `railway logs`
2. Проверьте переменные: `railway variables`
3. Проверьте статус: `railway status`
4. Обратитесь в Railway Support: support@railway.app

---

**Дата создания:** 2025-10-29
**Версия:** 1.0
**Автор:** Claude Code Assistant
