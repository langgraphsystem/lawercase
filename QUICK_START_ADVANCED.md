# 🚀 Quick Start - Advanced Features

**Версия:** 2.0 - Production Ready with LangGraph + WebSocket + Redis

---

## ⚡ Самый быстрый способ (все функции)

```bash
# 1. Запустить Redis (опционально, для production)
docker run -d -p 6379:6379 --name mega-redis redis:7-alpine

# 2. Установить зависимости
pip install langgraph redis[hiredis]

# 3. Настроить environment (опционально)
export USE_REDIS=true
export REDIS_URL=redis://localhost:6379/0
export USE_WEBSOCKET=true

# 4. Запустить API с WebSocket + LangGraph + Redis
python -m uvicorn api.main:app --reload --port 8000

# 5. Открыть браузер
http://localhost:8000/index.html

# 6. Включить WebSocket extension (опционально)
# Добавьте в index.html перед </body>:
<script src="websocket_extension.js"></script>
```

**Готово!** Теперь у вас:
- ✅ Real-time WebSocket updates
- ✅ LangGraph workflow с реальными агентами
- ✅ Redis persistence для горизонтального масштабирования

---

## 🎯 Варианты запуска

### Вариант 1: Minimal (без WebSocket и Redis)

```bash
python -m uvicorn api.main:app --reload
```

- Использует polling (каждые 2 секунды)
- Использует in-memory storage
- Использует mock workflow (без LangGraph)

### Вариант 2: WebSocket Only

```bash
# Установить websocket_extension.js
cp websocket_extension.js static/

# Запустить API
python -m uvicorn api.main:app --reload

# WebSocket автоматически активируется если:
# - В index.html установлен USE_WEBSOCKET: true
# - Или подключен websocket_extension.js
```

- ✅ Real-time updates через WebSocket
- Использует in-memory storage
- Использует mock workflow

### Вариант 3: LangGraph Only

```bash
# Установить LangGraph
pip install langgraph

# Запустить API
python -m uvicorn api.main:app --reload
```

- Использует polling или WebSocket
- Использует in-memory storage
- ✅ Использует real LangGraph workflow

### Вариант 4: Redis Only

```bash
# Запустить Redis
docker run -d -p 6379:6379 redis:7-alpine

# Установить redis
pip install redis[hiredis]

# Настроить
export USE_REDIS=true
export REDIS_URL=redis://localhost:6379/0

# Запустить API
python -m uvicorn api.main:app --reload
```

- Использует polling или WebSocket
- ✅ Использует Redis persistence
- Использует mock или real workflow

### Вариант 5: All Advanced Features (Production)

```bash
# 1. Запустить Redis
docker run -d -p 6379:6379 redis:7-alpine

# 2. Установить все зависимости
pip install langgraph redis[hiredis]

# 3. Настроить .env
cat > .env << EOF
USE_REDIS=true
REDIS_URL=redis://localhost:6379/0
USE_WEBSOCKET=true
EOF

# 4. Запустить production API
python -m uvicorn api.main_production:app --port 8000

# 5. Открыть
http://localhost:8000/static/index.html
```

- ✅ WebSocket real-time updates
- ✅ Redis persistence + horizontal scaling
- ✅ LangGraph workflow с real agents

---

## 🧪 Testing

### Test 1: Basic API

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### Test 2: Start Generation

```bash
curl -X POST http://localhost:8000/api/generate-petition \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "test-001",
    "document_type": "petition",
    "user_id": "test-user"
  }'

# Expected: {"thread_id": "...", "status": "generating", ...}
```

### Test 3: WebSocket (Browser Console)

```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/document/test-123');
ws.onopen = () => console.log('✅ WebSocket Connected');
ws.onmessage = (e) => console.log('📨 Message:', JSON.parse(e.data));
ws.send('ping'); // Test keep-alive
```

### Test 4: Redis (CLI)

```bash
redis-cli PING
# Expected: PONG

redis-cli KEYS "document_workflow:*"
# Expected: List of workflow keys

redis-cli GET "document_workflow:abc-123"
# Expected: JSON state
```

### Test 5: LangGraph Workflow

```bash
# Check logs after starting generation
# Look for one of:
# ✅ "using_real_workflow" - LangGraph успешно загружен
# ⚠️  "falling_back_to_mock_workflow" - Fallback на mock
```

---

## 📊 Feature Matrix

| Feature | Minimal | +WebSocket | +LangGraph | +Redis | Full |
|---------|---------|------------|------------|--------|------|
| Real-time Updates | Polling (2s) | **Instant** | Polling/WS | Polling/WS | **Instant** |
| Update Latency | 0-2000ms | **<100ms** | 0-2000ms | 0-2000ms | **<100ms** |
| Workflow | Mock | Mock | **Real** | Mock/Real | **Real** |
| Agents | None | None | **Writer+Validator** | None | **Writer+Validator** |
| Persistence | Memory | Memory | Memory | **Redis** | **Redis** |
| Horizontal Scale | ❌ | ❌ | ❌ | ✅ | ✅ |
| Production Ready | ❌ | ⚠️ | ⚠️ | ✅ | **✅** |

---

## 🔍 Проверка активных функций

### Проверить WebSocket

```bash
# В логах API должно быть:
# "websocket_connected" при подключении клиента
# "websocket_broadcast_sent" при broadcast

# В браузере console:
# [WebSocket] Connected to ws://localhost:8000/api/ws/document/...
# [WebSocket] Message: connected
```

### Проверить LangGraph

```bash
# В логах API должно быть:
# "using_real_workflow" - успех
# "generating_section" - генерация секции
# "section_workflow_completed" - завершение секции

# Или:
# "falling_back_to_mock_workflow" - fallback на mock
```

### Проверить Redis

```bash
# В логах API должно быть:
# "redis_connected" при старте
# "document_workflow_saved_redis" при сохранении
# "document_workflow_loaded_redis" при загрузке

# Redis CLI:
redis-cli
> KEYS document_workflow:*
> GET document_workflow:abc-123
```

---

## 🐛 Troubleshooting

### WebSocket не работает

**Проблема:** "WebSocket connection failed"

**Решение:**
```bash
# 1. Проверить, что API запущен
curl http://localhost:8000/health

# 2. Проверить URL в index.html
# Должен быть: ws://localhost:8000/api/ws/document/{thread_id}

# 3. Проверить CORS
# В api/main.py должен быть CORSMiddleware

# 4. Fallback на polling автоматически активируется
```

### LangGraph не работает

**Проблема:** "LangGraph is required"

**Решение:**
```bash
# Установить LangGraph
pip install langgraph

# Проверить импорт
python -c "import langgraph; print('OK')"

# Если ошибка - система автоматически использует mock mode
```

### Redis не подключается

**Проблема:** "redis_connection_failed"

**Решение:**
```bash
# 1. Проверить, что Redis запущен
redis-cli ping

# 2. Если нет - запустить
docker run -d -p 6379:6379 redis:7-alpine

# 3. Проверить REDIS_URL
echo $REDIS_URL

# 4. Если ошибка - система автоматически использует in-memory
```

### Port уже занят

**Проблема:** "Address already in use"

**Решение:**
```bash
# Использовать другой порт
python -m uvicorn api.main:app --reload --port 8080

# Обновить URL в браузере
http://localhost:8080/index.html
```

---

## 📚 Дополнительная документация

- **WebSocket:** См. `ADVANCED_FEATURES_COMPLETE.md` → раздел "WebSocket Real-Time Updates"
- **LangGraph:** См. `ADVANCED_FEATURES_COMPLETE.md` → раздел "Real LangGraph Workflow"
- **Redis:** См. `REDIS_CONFIGURATION.md`
- **Базовая интеграция:** См. `DOCUMENT_MONITOR_INTEGRATION_GUIDE.md`

---

## ✅ Checklist готовности

### Development

- [ ] API запускается: `python -m uvicorn api.main:app --reload`
- [ ] index.html открывается: `http://localhost:8000/index.html`
- [ ] Mock режим работает: кнопка "🧪 Use Mock Data"
- [ ] Генерация запускается: кнопка "🚀 Начать генерацию"

### Production (опционально)

- [ ] Redis запущен: `redis-cli ping` → PONG
- [ ] LangGraph установлен: `pip show langgraph`
- [ ] Environment настроен: `.env` файл создан
- [ ] WebSocket работает: см. Browser Console
- [ ] Логи показывают "using_real_workflow"
- [ ] Логи показывают "redis_connected"

---

## 🎯 Recommended Setup

**For Development:**
```bash
python -m uvicorn api.main:app --reload
# Открыть: http://localhost:8000/index.html
# Использовать: Mock Data
```

**For Testing:**
```bash
docker run -d -p 6379:6379 redis:7-alpine
pip install langgraph redis[hiredis]
export USE_REDIS=true
python -m uvicorn api.main:app --reload
# Открыть: http://localhost:8000/index.html
# Использовать: Real workflow + WebSocket + Redis
```

**For Production:**
```bash
# См. ADVANCED_FEATURES_COMPLETE.md → Deployment Guide
docker-compose -f docker-compose.prod.yml up -d
```

---

**Status:** ✅ Ready to run!

Выберите нужный вариант и следуйте инструкциям. Все функции работают независимо и имеют автоматический fallback.
