# Railway CLI Commands - Environment Variables Update

**Дата**: 2025-11-13
**Цель**: Установить PUBLIC_BASE_URL в Railway для автоматической установки webhook

---

## 🎯 Проблема

Webhook автоматически переключается на старый URL при каждом деплое, потому что в Railway environment variables указан старый адрес или не указан вообще.

**Решение**: Установить `PUBLIC_BASE_URL` через Railway CLI.

---

## 📋 Railway Service Details

```bash
RAILWAY_PROJECT_ID: fdb326fc-d5b9-4110-86d1-b8233d4bc970
RAILWAY_ENVIRONMENT_ID: 7b5af35c-3118-416b-82b8-a0590ef9b460
RAILWAY_SERVICE_ID: 3b598693-2e3c-4089-8fdb-ed9cbd8f68e0
RAILWAY_SERVICE_NAME: refreshing-reprieve
```

**Deployment URL**: `https://refreshing-reprieve-production-9802.up.railway.app`

---

## 🚀 Railway CLI Commands

### 1. Проверка текущих переменных

```bash
# Link to the project (if not already linked)
railway link fdb326fc-d5b9-4110-86d1-b8233d4bc970

# List all current variables
railway variables
```

### 2. Установка PUBLIC_BASE_URL

```bash
# Set PUBLIC_BASE_URL for the service
railway variables --set PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app
```

**Или** используйте полный формат с указанием environment и service:

```bash
railway variables set \
  --environment 7b5af35c-3118-416b-82b8-a0590ef9b460 \
  --service 3b598693-2e3c-4089-8fdb-ed9cbd8f68e0 \
  PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app
```

### 3. Проверка установленной переменной

```bash
# Verify the variable was set
railway variables | grep PUBLIC_BASE_URL
```

**Ожидаемый результат**:
```
PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app
```

### 4. Redeploy сервиса

После установки переменной нужно передеплоить:

```bash
# Option A: Trigger redeploy via Railway CLI
railway up

# Option B: Trigger redeploy without uploading code
railway redeploy
```

**Или** просто сделайте пуш в Git - Railway автоматически задеплоит:

```bash
git commit --allow-empty -m "Trigger Railway redeploy"
git push origin hardening/roadmap-v1
```

---

## ✅ Проверка после деплоя

### 1. Проверьте логи деплоя

```bash
railway logs --tail 100
```

**Ищите строку**:
```
webhook.url.derived url=https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook
```

### 2. Проверьте webhook через Telegram API

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python -m json.tool
```

**Ожидаемый результат**:
```json
{
  "url": "https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook",
  "pending_update_count": 0
}
```

### 3. Проверьте health endpoint

```bash
curl "https://refreshing-reprieve-production-9802.up.railway.app/health"
```

**Ожидаемый результат**:
```json
{
  "status": "healthy",
  "memory_system": true,
  "case_agent": true
}
```

---

## 🔧 Альтернатива: Railway Dashboard

Если Railway CLI не работает, можно установить через Dashboard:

1. Откройте https://railway.app/project/fdb326fc-d5b9-4110-86d1-b8233d4bc970
2. Выберите service **refreshing-reprieve**
3. Перейдите в **Settings** → **Variables**
4. Нажмите **+ New Variable**
5. Добавьте:
   - **Name**: `PUBLIC_BASE_URL`
   - **Value**: `https://refreshing-reprieve-production-9802.up.railway.app`
6. Нажмите **Add**
7. Railway автоматически передеплоит сервис

---

## 📊 Как это работает

См. [api/main.py:176-212](api/main.py#L176-L212):

```python
def _build_webhook_url(settings: AppSettings) -> str:
    """Build webhook URL from environment variables.

    Priority order:
    1. PUBLIC_BASE_URL (explicit) ← МЫ УСТАНАВЛИВАЕМ ЭТОТ
    2. RAILWAY_STATIC_URL (Railway-generated)
    3. RAILWAY_PUBLIC_DOMAIN (Railway domain only)
    """

    base = (
        settings.public_base_url         # Приоритет 1
        or settings.railway_static_url   # Приоритет 2
        or (f"https://{settings.railway_public_domain}"
            if settings.railway_public_domain else None)  # Приоритет 3
    )

    if not base:
        raise ValueError("No public URL configured")

    webhook_url = f"{base}/telegram/webhook"
    logger.info("webhook.url.derived", url=webhook_url)
    return webhook_url
```

**При старте API**:
1. Читает `PUBLIC_BASE_URL` из переменных окружения
2. Строит `webhook_url = "https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook"`
3. Автоматически устанавливает webhook через Telegram Bot API
4. Логирует `webhook.configured` event

---

## ⚠️ Текущий статус

### До установки переменной

- ❌ Webhook автоматически устанавливается на старый URL
- ❌ Получает 404 Not Found
- ❌ Нужно вручную обновлять после каждого деплоя

### После установки переменной

- ✅ Webhook автоматически устанавливается на правильный URL
- ✅ Работает сразу после деплоя
- ✅ Не нужно ручное вмешательство

---

## 🔗 Related Files

- [RAILWAY_ENV_UPDATE.md](RAILWAY_ENV_UPDATE.md) - Полная документация по переменным
- [WEBHOOK_UPDATE_2025-11-13.md](WEBHOOK_UPDATE_2025-11-13.md) - Ручное обновление webhook
- [api/main.py](api/main.py#L176-L212) - Логика построения webhook URL
- [config/settings.py](config/settings.py) - Environment variables definition

---

## 📝 Summary

**Одна команда для решения проблемы**:

```bash
railway variables --set PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app && railway redeploy
```

**Проверка**:
```bash
railway logs --tail 50 | grep webhook
```

**Status**: 📝 Инструкции готовы
**Action Required**: Выполнить команду выше
**Expected Result**: Webhook устанавливается автоматически при каждом деплое

🤖 Generated with [Claude Code](https://claude.com/claude-code)
