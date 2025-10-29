# Railway Quick Start - MegaAgent Pro

Быстрое развертывание на Railway за 5 минут.

## 1. Подготовка (1 минута)

```bash
# Проверьте конфигурацию
python verify_railway_config.py

# Должен вывести: ✅ All critical checks PASSED!
```

## 2. Создание проекта Railway (2 минуты)

### Вариант A: Через веб-интерфейс

1. Откройте https://railway.app
2. Нажмите **"New Project"**
3. Выберите **"Deploy from GitHub repo"**
4. Выберите `mega_agent_pro_codex_handoff`
5. Railway автоматически начнет деплой

### Вариант B: Через CLI

```bash
# Установите Railway CLI
npm i -g @railway/cli

# Войдите
railway login

# Создайте проект
railway init

# Подключите GitHub
railway link

# Деплой
railway up
```

## 3. Добавление PostgreSQL (30 секунд)

В Railway Dashboard:

1. Нажмите **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway создаст базу данных
3. Скопируйте `DATABASE_URL` из переменных

## 4. Настройка переменных окружения (2 минуты)

В Railway Dashboard → Your Project → Variables:

### Минимальный набор для запуска:

```bash
# Database (автоматически из PostgreSQL сервиса)
POSTGRES_DSN=postgresql+asyncpg://user:pass@host:5432/db  # pragma: allowlist secret
DATABASE_URL=postgresql://user:pass@host:5432/db  # pragma: allowlist secret
PG_DSN=postgresql://user:pass@host:5432/db  # pragma: allowlist secret

# OpenAI API (ОБЯЗАТЕЛЬНО)
OPENAI_API_KEY=sk-proj-your-key-here
LLM_OPENAI_API_KEY=sk-proj-your-key-here

# Security (ОБЯЗАТЕЛЬНО)
JWT_SECRET_KEY=your-secret-key-min-32-chars

# Environment
ENV=production
PYTHONUNBUFFERED=1
```

### Опциональные переменные:

```bash
# Gemini (для дополнительных LLM функций)
GEMINI_API_KEY=your-gemini-key
LLM_GEMINI_API_KEY=your-gemini-key

# Pinecone (для векторного поиска)
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=mega-agent-semantic

# Telegram Bot
TELEGRAM_BOT_TOKEN=7472625853:AAG...
TELEGRAM_ALLOWED_USERS=123456,789012

# Voyage AI (для эмбеддингов)
VOYAGE_API_KEY=your-voyage-key

# Cloudflare R2 (для хранения файлов)
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=mega-agent-documents
```

**ВАЖНО:** НЕ устанавливайте переменную `PORT` - Railway делает это автоматически!

## 5. Проверка деплоя (30 секунд)

### Через Dashboard:

1. Откройте **Deployments** → посмотрите логи
2. Дождитесь статуса **"Success"**
3. Откройте **Settings** → скопируйте **Public URL**

### Через CLI:

```bash
# Логи
railway logs

# Статус
railway status

# Получить URL
railway domain
```

### Проверка health endpoint:

```bash
# Замените URL на ваш
curl https://your-app.railway.app/health

# Ожидаемый ответ:
{
  "status": "healthy",
  "environment": "production",
  "version": "1.0.0"
}
```

## 6. Тестовый запрос (30 секунд)

```bash
# Тест API
curl -X POST https://your-app.railway.app/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello!"}'

# Должен вернуть ответ от GPT-5
```

## Готово!

Ваш MegaAgent Pro запущен на Railway! 🚀

---

## Telegram Bot (опционально)

Для запуска Telegram бота как отдельного сервиса:

1. В Railway Dashboard нажмите **"New Service"**
2. Выберите тот же GitHub репозиторий
3. В Settings → Build:
   - Docker Build Target: `bot`
4. Добавьте переменные:
   ```bash
   TELEGRAM_BOT_TOKEN=your-token
   OPENAI_API_KEY=sk-proj-...
   POSTGRES_DSN=postgresql+asyncpg://...
   ```
5. Deploy!

Проверка бота:
```bash
# Отправьте /start боту в Telegram
# Должен ответить приветствием
```

---

## Полезные команды

```bash
# Посмотреть логи
railway logs --follow

# Перезапустить сервис
railway restart

# Откатить деплой
railway rollback

# Локальный запуск с Railway переменными
railway run python -m uvicorn api.main_production:app

# Открыть Dashboard
railway open
```

---

## Проблемы?

### Build Failed

```bash
# Проверьте конфигурацию
python verify_railway_config.py

# Проверьте логи билда
railway logs
```

### API не отвечает

```bash
# Проверьте переменные
railway variables

# Убедитесь что OPENAI_API_KEY и DATABASE_URL установлены
```

### База данных не подключается

```bash
# В Railway Dashboard:
# 1. Откройте PostgreSQL сервис
# 2. Скопируйте DATABASE_URL
# 3. Установите:
#    POSTGRES_DSN = DATABASE_URL с заменой postgresql:// на postgresql+asyncpg://
```

---

## Что дальше?

- Полное руководство: [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)
- Настройка Telegram бота: [BOT_QUICKSTART.md](BOT_QUICKSTART.md)
- GPT-5 интеграция: [GPT5_INTEGRATION.md](GPT5_INTEGRATION.md)
- Мониторинг и логи: Railway Dashboard → Metrics

---

**Railway Support:** https://railway.app/help
**Discord:** https://discord.gg/railway
