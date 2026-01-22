# Railway Environment Variables Update

**Дата**: 2025-11-13
**Причина**: Обновление webhook URL на новый Railway deployment

---

## ⚠️ Проблема

Webhook автоматически переключается на старый URL при каждом деплое, потому что в Railway environment variables указан старый адрес.

**Текущее поведение**:
```
API запускается → Читает PUBLIC_BASE_URL/RAILWAY_STATIC_URL
→ Устанавливает webhook на старый URL
→ Получает 404 Not Found
```

---

## ✅ Решение

Обновить environment variables в Railway Dashboard для правильного webhook URL.

### 1. Откройте Railway Dashboard

```
https://railway.app/project/<project-id>
→ Service: lawercase
→ Settings → Variables
```

### 2. Обновите следующие переменные

#### Option A: Используйте PUBLIC_BASE_URL (рекомендуется)

```bash
PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app
```

**Приоритет**: Highest - будет использован первым

#### Option B: Используйте RAILWAY_STATIC_URL

```bash
RAILWAY_STATIC_URL=https://refreshing-reprieve-production-9802.up.railway.app
```

**Приоритет**: Medium - если PUBLIC_BASE_URL не установлен

#### Option C: Используйте RAILWAY_PUBLIC_DOMAIN

```bash
RAILWAY_PUBLIC_DOMAIN=refreshing-reprieve-production-9802.up.railway.app
```

**Приоритет**: Lowest - код добавит `https://` автоматически

---

## 📋 Полный список переменных для обновления

```bash
# === PRIMARY CONFIGURATION ===
PUBLIC_BASE_URL=https://refreshing-reprieve-production-9802.up.railway.app

# === TELEGRAM ===
TELEGRAM_BOT_TOKEN=<ваш токен>
TELEGRAM_WEBHOOK_SECRET=<ваш секрет>
TELEGRAM_ALLOWED_USERS=<список user_id>

# === OPENAI ===
OPENAI_API_KEY=<ваш ключ>
```

---

## 🔍 Как проверить текущие переменные

### В Railway Dashboard:
```
Project → Service → Settings → Variables
```

### Через Railway CLI:
```bash
railway variables
```

---

## 🔧 Логика построения webhook URL

См. [api/main.py:176-212](api/main.py#L176-L212):

```python
def _build_webhook_url(settings: AppSettings) -> str:
    """Build webhook URL from environment variables.

    Priority order:
    1. PUBLIC_BASE_URL (explicit)
    2. RAILWAY_STATIC_URL (Railway-generated)
    3. RAILWAY_PUBLIC_DOMAIN (Railway domain only, adds https://)
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
    return webhook_url
```

---

## ✅ После обновления переменных

### 1. Redeploy сервис в Railway

Railway Dashboard → Deployments → Redeploy

**ИЛИ**

Просто закоммитить любое изменение и запушить в GitHub - Railway автоматически задеплоит.

### 2. Проверьте webhook

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

**Ожидаемый результат**:
```json
{
  "url": "https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook",
  "pending_update_count": 0
}
```

### 3. Проверьте health

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

## 📝 Альтернатива: Ручная установка webhook после деплоя

Если не хотите обновлять переменные в Railway, можно вручную устанавливать webhook после каждого деплоя:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://refreshing-reprieve-production-9802.up.railway.app/telegram/webhook",
    "secret_token": "<ваш секрет>",
    "max_connections": 40
  }'
```

**Минусы**: Нужно делать после каждого деплоя вручную

---

## 🎯 Рекомендуемое решение

**Лучший вариант**: Обновить `PUBLIC_BASE_URL` в Railway Variables

**Преимущества**:
- ✅ Webhook устанавливается автоматически при старте
- ✅ Не нужно ручное вмешательство после деплоя
- ✅ Консистентная конфигурация
- ✅ Документировано в коде

---

## 🔗 Related Files

- [WEBHOOK_UPDATE_2025-11-13.md](WEBHOOK_UPDATE_2025-11-13.md) - Ручное обновление webhook
- [api/main.py](api/main.py#L176-L212) - Логика построения webhook URL
- [config/settings.py](config/settings.py#L31-L33) - Environment variables definition

---

**Status**: 📝 Инструкция готова
**Next Step**: Обновить переменные в Railway Dashboard
**Expected Result**: Webhook устанавливается автоматически на правильный URL

🤖 Generated with [Claude Code](https://claude.com/claude-code)
