# Railway Deployment Status - 2025-11-13

**Дата**: 2025-11-13 23:45 UTC
**Branch**: hardening/roadmap-v1
**Последний коммит**: f694b4e

---

## ✅ Что Работает

### 1. Telegram Webhook (Временно)
- ✅ Webhook обновлен вручную на новый URL
- ✅ URL: `https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook`
- ✅ Pending updates: 0
- ✅ Status: Working
- ✅ IP: 66.33.22.157

**Проверка**:
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
# "url": "https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook",
# "pending_update_count": 0
```

### 2. Case Management System
- ✅ `/case_create <title> | description` - работает
- ✅ `/case_get <case_id>` - работает
- ✅ `/case_active` - работает
- ✅ Автоматический выбор созданного кейса в RMT
- ✅ Thread ID format: `"tg:<chat_id>"`
- ✅ Хранение active_case_id в RMT memory

### 3. Документация
- ✅ [RAILWAY_CLI_COMMANDS.md](RAILWAY_CLI_COMMANDS.md) - Конкретные команды Railway CLI
- ✅ [RAILWAY_ENV_UPDATE.md](RAILWAY_ENV_UPDATE.md) - Полная документация по env vars
- ✅ [WEBHOOK_UPDATE_2025-11-13.md](WEBHOOK_UPDATE_2025-11-13.md) - История обновлений webhook

---

## ⚠️ Известные Проблемы

### Проблема 1: Webhook Reverts on Deploy

**Симптом**: После каждого деплоя webhook переключается на старый URL
```
https://lawercase-production.up.railway.app/telegram/webhook  ← СТАРЫЙ
```

**Root Cause**: В Railway environment variables не установлен `PUBLIC_BASE_URL`

**Impact**:
- ❌ Webhook получает 404 Not Found
- ❌ Бот не отвечает на команды
- ❌ Нужно вручную обновлять webhook после каждого деплоя

**Решение**: См. [RAILWAY_CLI_COMMANDS.md](RAILWAY_CLI_COMMANDS.md)

### Проблема 2: Railway Startup Error (Logger TypeError)

**Симптом**: Railway deployment fails with:
```
TypeError: Logger._log() got an unexpected keyword argument 'group'
  File "/app/telegram_interface/middlewares/di_injection.py", line 96
  logger.info("telegram.di.middleware_installed", group=-1)
```

**Root Cause**:
- Railway кэширует старый Docker image
- Старый образ содержал `import logging` вместо `import structlog`
- Локальный файл уже исправлен в коммите 0c348c6

**Impact**:
- ❌ API не запускается на Railway
- ❌ Telegram bot не работает
- ⚠️ Webhook был обновлен вручную, но API может быть недоступен

**Статус**: Локально исправлено, но Railway использует кэш

**Возможные решения**:
1. **Railway Dashboard** → Deployments → Settings → "Clear build cache" → Redeploy
2. **Railway CLI**: `railway redeploy --no-cache`
3. **Обновить Dockerfile** чтобы инвалидировать кэш (добавить комментарий)

---

## 🎯 Действия для Постоянного Решения

### Action 1: Установить PUBLIC_BASE_URL в Railway

**Цель**: Автоматическая установка webhook при каждом деплое

**Railway CLI** (рекомендуется):
```bash
# Link to project
railway link fdb326fc-d5b9-4110-86d1-b8233d4bc970

# Set variable
railway variables --set PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app

# Verify
railway variables | grep PUBLIC_BASE_URL
```

**Railway Dashboard** (альтернатива):
1. Откройте https://railway.app/project/fdb326fc-d5b9-4110-86d1-b8233d4bc970
2. Service: **refreshing-reprieve**
3. Settings → Variables → + New Variable
4. Name: `PUBLIC_BASE_URL`
5. Value: `https://refreshing-reprieve-production-9802.up.railway.app`
6. Add

### Action 2: Clear Railway Build Cache

**Цель**: Заставить Railway использовать новый код (structlog fix)

**Railway Dashboard**:
1. https://railway.app/project/fdb326fc-d5b9-4110-86d1-b8233d4bc970
2. Service: **refreshing-reprieve**
3. Latest Deployment → ⋮ → Redeploy (with "Clear cache" option if available)

**Railway CLI**:
```bash
railway redeploy --no-cache
```

**Git Trigger** (может не помочь если кэш):
```bash
git commit --allow-empty -m "Force Railway rebuild"
git push origin hardening/roadmap-v1
```

### Action 3: Verify Deployment

После выполнения Actions 1 & 2, проверьте:

**1. Railway Logs**:
```bash
railway logs --tail 100
```

**Ищите**:
```
✅ webhook.url.derived url=https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook
✅ webhook.configured successfully
✅ telegram.di.middleware_installed  # БЕЗ ошибки Logger
```

**2. Webhook Status**:
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python -m json.tool
```

**Ожидается**:
```json
{
  "url": "https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook",
  "pending_update_count": 0
}
```

**3. Health Check**:
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

**4. Test Bot**:
```
/start
/help
/case_create Test Case | Test Description
/case_active
```

---

## 📊 Railway Service Details

```bash
Project ID:     fdb326fc-d5b9-4110-86d1-b8233d4bc970
Environment ID: 7b5af35c-3118-416b-82b8-a0590ef9b460
Service ID:     3b598693-2e3c-4089-8fdb-ed9cbd8f68e0
Service Name:   refreshing-reprieve

Deployment URL: https://refreshing-reprieve-production-9802.up.railway.app
Branch:         hardening/roadmap-v1
Last Commit:    f694b4e
```

---

## 🔄 Workflow После Исправления

После установки `PUBLIC_BASE_URL` и clearing cache:

1. **Git Push** → Railway автоматически деплоит
2. **Startup** → API читает `PUBLIC_BASE_URL` из env vars
3. **Webhook** → Автоматически устанавливается на правильный URL
4. **Bot** → Сразу работает, без ручного вмешательства

**Больше не нужно**:
- ❌ Ручное обновление webhook после деплоя
- ❌ curl commands к Telegram API
- ❌ Мониторинг pending_update_count

---

## 📝 Технические Детали

### Webhook Auto-Configuration Logic

См. [api/main.py:176-212](api/main.py#L176-L212):

```python
def _build_webhook_url(settings: AppSettings) -> str:
    """Build webhook URL from environment variables.

    Priority:
    1. PUBLIC_BASE_URL (explicit) ← УСТАНАВЛИВАЕМ ЭТОТ
    2. RAILWAY_STATIC_URL (auto-generated)
    3. RAILWAY_PUBLIC_DOMAIN (domain only, adds https://)
    """

    base = (
        settings.public_base_url         # Highest priority
        or settings.railway_static_url
        or (f"https://{settings.railway_public_domain}"
            if settings.railway_public_domain else None)
    )

    if not base:
        raise ValueError("No public URL configured for webhook")

    webhook_url = f"{base}/telegram/webhook"
    logger.info("webhook.url.derived", url=webhook_url, source=...)
    return webhook_url
```

### Case Management RMT Storage

См. [telegram_interface/handlers/context.py:45-67](telegram_interface/handlers/context.py#L45-L67):

```python
async def set_active_case(self, update, case_id: str) -> None:
    """Persist active case id for this chat in RMT."""
    thread_id = self.thread_id_for_update(update)  # "tg:<chat_id>"

    slots = await self.mega_agent.memory.aget_rmt(thread_id)
    if not slots:
        slots = {"persona": "", "long_term_facts": "", ...}

    slots["active_case_id"] = str(case_id)
    await self.mega_agent.memory.aset_rmt(thread_id, slots)
```

---

## 🔗 Related Files

- [RAILWAY_CLI_COMMANDS.md](RAILWAY_CLI_COMMANDS.md) - Specific Railway CLI commands
- [RAILWAY_ENV_UPDATE.md](RAILWAY_ENV_UPDATE.md) - Environment variables guide
- [WEBHOOK_UPDATE_2025-11-13.md](WEBHOOK_UPDATE_2025-11-13.md) - Manual webhook update log
- [api/main.py](api/main.py#L176-L212) - Webhook auto-configuration code
- [telegram_interface/handlers/case_handlers.py](telegram_interface/handlers/case_handlers.py) - Case management handlers
- [telegram_interface/handlers/context.py](telegram_interface/handlers/context.py) - RMT storage helpers

---

## 📈 Next Steps Priority

| # | Action | Priority | Impact | Effort |
|---|--------|----------|--------|--------|
| 1 | Set PUBLIC_BASE_URL in Railway | 🔴 CRITICAL | High | Low (1 command) |
| 2 | Clear Railway build cache | 🔴 CRITICAL | High | Low (1 click) |
| 3 | Verify deployment success | 🟡 HIGH | Medium | Low (run tests) |
| 4 | Monitor Railway logs | 🟢 MEDIUM | Low | Low (passive) |

---

**Current Status**: ⚠️ Webhook working (manual), Railway deployment failing (cache)
**Required Actions**: 2 critical (set env var, clear cache)
**Estimated Time**: 5-10 minutes
**Expected Result**: Fully automated webhook configuration on every deploy

🤖 Generated with [Claude Code](https://claude.com/claude-code)
