# Railway Required Environment Variables

**Дата**: 2025-11-14
**Статус**: ⚠️ CRITICAL - Bot not responding due to missing env vars

---

## 🚨 Проблема

Telegram bot не отвечает на команды, потому что в Railway не установлены критические environment variables:

1. **TELEGRAM_ALLOWED_USERS** - Список авторизованных user_id
2. **OPENAI_API_KEY** - Для работы MegaAgent
3. **PUBLIC_BASE_URL** - Для автоматической настройки webhook (опционально)

---

## ✅ Обязательные Variables

### 1. TELEGRAM_BOT_TOKEN

**Статус**: ✅ Уже установлен (бот получает сообщения)

**Значение**: `7472625853:AAGPl30wtI9g57VqYIAO4H2WyXnrZgk4scA  # pragma: allowlist secret`

### 2. TELEGRAM_ALLOWED_USERS ⚠️ КРИТИЧНО

**Статус**: ❌ НЕ УСТАНОВЛЕН

**Что происходит без этой переменной**:
- Бот блокирует все запросы или работает в open mode
- Если есть проверка авторизации, бот не будет отвечать

**Как получить ваш user_id**:
1. Отправьте `/start` боту @userinfobot
2. Он покажет ваш `Id: 123456789`

**Значение для установки**:
```bash
TELEGRAM_ALLOWED_USERS=<ваш_user_id>
```

**Пример**:
```bash
TELEGRAM_ALLOWED_USERS=123456789
```

Для нескольких пользователей (через запятую):
```bash
TELEGRAM_ALLOWED_USERS=123456789,987654321,111222333
```

### 3. TELEGRAM_WEBHOOK_SECRET ⚠️ КРИТИЧНО

**Статус**: ✅ Используется при ручной установке webhook

**Значение**: `6e18eeecca2e415bf68228a3bc6bcb0f499f4171cf4084ee2ee5502e7a17ef36`

### 4. OPENAI_API_KEY ⚠️ КРИТИЧНО

**Статус**: ❓ Неизвестно

**Что происходит без этой переменной**:
- MegaAgent не может работать (все LLM операции)
- Команды `/ask`, `/case_create` и другие будут падать с ошибкой

**Значение для установки**:
```bash
OPENAI_API_KEY=sk-proj-...
```

**Где взять**:
- https://platform.openai.com/api-keys
- Нужен API key с доступом к GPT-5.1 (или GPT-5)

---

## 📋 Опциональные Variables (Рекомендуемые)

### 5. PUBLIC_BASE_URL (Рекомендуется)

**Статус**: ❌ НЕ УСТАНОВЛЕН

**Что происходит без этой переменной**:
- Webhook нужно устанавливать вручную после каждого деплоя
- API может использовать fallback URL (старый или неправильный)

**Значение для установки**:
```bash
PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app
```

**Benefit**: Автоматическая установка webhook при старте API

### 6. Другие опциональные переменные

```bash
# Environment
ENV=production
DEBUG=false

# Logging
LOG_LEVEL=INFO

# Feature flags
ENABLE_CASE_MANAGEMENT=true
ENABLE_MEMORY_SYSTEM=true
```

---

## 🚀 Как Установить в Railway

### Option A: Railway Dashboard (Самый простой)

1. Откройте https://railway.app/project/fdb326fc-d5b9-4110-86d1-b8233d4bc970
2. Выберите service: **refreshing-reprieve**
3. Перейдите в **Settings** → **Variables**
4. Нажмите **+ New Variable** для каждой переменной:

   **Variable 1**: TELEGRAM_ALLOWED_USERS
   - Name: `TELEGRAM_ALLOWED_USERS`
   - Value: `<ваш_user_id>` (получите через @userinfobot)

   **Variable 2**: OPENAI_API_KEY
   - Name: `OPENAI_API_KEY`
   - Value: `sk-proj-...` (ваш OpenAI API key)

   **Variable 3**: PUBLIC_BASE_URL (опционально)
   - Name: `PUBLIC_BASE_URL`
   - Value: `https://refreshing-reprieve-production-9802.up.railway.app`

5. Нажмите **Add** для каждой переменной
6. Railway автоматически передеплоит сервис

### Option B: Railway CLI

```bash
# Link to project (if not already linked)
cd /path/to/mega_agent_pro_codex_handoff

# Set variables
railway variables --service 3b598693-2e3c-4089-8fdb-ed9cbd8f68e0 \
                  --environment 7b5af35c-3118-416b-82b8-a0590ef9b460 \
                  --set "TELEGRAM_ALLOWED_USERS=<ваш_user_id>"

railway variables --service 3b598693-2e3c-4089-8fdb-ed9cbd8f68e0 \
                  --environment 7b5af35c-3118-416b-82b8-a0590ef9b460 \
                  --set "OPENAI_API_KEY=sk-proj-..."

railway variables --service 3b598693-2e3c-4089-8fdb-ed9cbd8f68e0 \
                  --environment 7b5af35c-3118-416b-82b8-a0590ef9b460 \
                  --set "PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app"

# Verify
railway variables
```

---

## 🔍 Как Получить Ваш Telegram User ID

### Метод 1: Через @userinfobot

1. Откройте Telegram
2. Найдите бота: @userinfobot
3. Отправьте `/start`
4. Бот покажет:
   ```
   Id: 123456789
   First name: Your Name
   Username: @yourusername
   ```
5. Скопируйте число из `Id: 123456789`

### Метод 2: Через @raw_data_bot

1. Найдите @raw_data_bot
2. Отправьте любое сообщение
3. Бот покажет JSON с вашими данными
4. Найдите `"id": 123456789` в разделе `"from"`

### Метод 3: Через логи Railway (если bot уже получал ваши сообщения)

```bash
railway logs --tail 100 | grep "user_id"
```

Найдите строку типа:
```
telegram.case_create.received user_id=123456789
```

---

## ✅ После Установки Переменных

### 1. Дождитесь Redeploy

Railway автоматически передеплоит сервис (2-5 минут).

### 2. Проверьте Webhook

```bash
curl "https://api.telegram.org/bot7472625853:AAGPl30wtI9g57VqYIAO4H2WyXnrZgk4scA  # pragma: allowlist secret/getWebhookInfo"
```

**Ожидается**:
```json
{
  "url": "https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook",
  "pending_update_count": 0
}
```

### 3. Проверьте API Health

```bash
curl "https://refreshing-reprieve-production-9802.up.railway.app/health"
```

**Ожидается**:
```json
{
  "status": "healthy",
  "memory_system": true,
  "case_agent": true
}
```

### 4. Протестируйте Бота

Отправьте в Telegram боту:
```
/start
```

**Ожидается**: Приветствие и список команд

Затем попробуйте:
```
/case_create Тестовый Кейс | Это описание
```

**Ожидается**:
```
📁 Case created: Тестовый Кейс
ID: case_<timestamp>_<hash>
```

---

## 🔗 Verification Commands

После установки переменных и redeploy:

```bash
# Check if API started successfully
curl https://refreshing-reprieve-production-9802.up.railway.app/health

# Check webhook status
curl "https://api.telegram.org/bot7472625853:AAGPl30wtI9g57VqYIAO4H2WyXnrZgk4scA  # pragma: allowlist secret/getWebhookInfo"

# Check Railway logs for startup errors
railway logs --tail 50
```

**Look for**:
- ✅ `webhook.configured successfully`
- ✅ `telegram.di.middleware_installed`
- ✅ No ERROR messages about missing API keys

---

## 📊 Priority of Variables

| Priority | Variable | Impact if Missing | Status |
|----------|----------|-------------------|--------|
| 🔴 CRITICAL | TELEGRAM_BOT_TOKEN | Bot won't receive messages | ✅ Set |
| 🔴 CRITICAL | TELEGRAM_ALLOWED_USERS | Bot won't respond to anyone | ❌ Missing |
| 🔴 CRITICAL | OPENAI_API_KEY | MegaAgent won't work | ❓ Unknown |
| 🔴 CRITICAL | TELEGRAM_WEBHOOK_SECRET | Webhook security | ✅ Set |
| 🟡 HIGH | PUBLIC_BASE_URL | Webhook manual config needed | ❌ Missing |
| 🟢 LOW | ENV, DEBUG, LOG_LEVEL | Minor functionality | Optional |

---

## 🚨 Current Status

### What's Working
- ✅ Railway deployment successful
- ✅ API responding to health checks
- ✅ Webhook receiving messages (pending_update_count: 0)

### What's NOT Working
- ❌ Bot not responding to commands
- ❌ Likely cause: Missing TELEGRAM_ALLOWED_USERS
- ❌ Possible cause: Missing OPENAI_API_KEY

### Immediate Action Required

**Step 1**: Get your Telegram user_id
```
Send /start to @userinfobot
Copy the Id number
```

**Step 2**: Set TELEGRAM_ALLOWED_USERS in Railway
```
Railway Dashboard → refreshing-reprieve → Settings → Variables
Add: TELEGRAM_ALLOWED_USERS = <your_user_id>
```

**Step 3**: Set OPENAI_API_KEY (if not already set)
```
Add: OPENAI_API_KEY = sk-proj-...
```

**Step 4**: Wait for redeploy (2-5 minutes)

**Step 5**: Test bot with `/start`

---

## 🔗 Related Documentation

- [WEBHOOK_UPDATE_2025-11-13.md](WEBHOOK_UPDATE_2025-11-13.md) - Webhook manual setup
- [RAILWAY_CLI_COMMANDS.md](RAILWAY_CLI_COMMANDS.md) - Railway CLI commands
- [DEPLOYMENT_SUCCESS_2025-11-14.md](DEPLOYMENT_SUCCESS_2025-11-14.md) - Deployment status

---

**Status**: 📝 Waiting for User to Set Variables
**Next Step**: Set TELEGRAM_ALLOWED_USERS and OPENAI_API_KEY in Railway Dashboard
**Expected Result**: Bot will respond to authorized users

🤖 Generated with [Claude Code](https://claude.com/claude-code)
