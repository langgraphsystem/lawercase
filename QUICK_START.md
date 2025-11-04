# 🚀 Quick Start - Document Monitor

## Запуск за 30 секунд

### Вариант 1: С Backend API

```bash
# 1. Запустить FastAPI сервер
python -m uvicorn api.main:app --reload --port 8000

# 2. Открыть браузер
http://localhost:8000/index.html

# 3. Готово! ✅
```

### Вариант 2: Автономно (Mock режим)

```bash
# 1. Открыть index.html напрямую
start index.html  # Windows
open index.html   # macOS
xdg-open index.html  # Linux

# 2. Нажать "🧪 Use Mock Data"

# 3. Нажать "🚀 Начать генерацию"

# 4. Готово! ✅
```

---

## Что дальше?

### Протестировать функции:
1. **Загрузить Exhibit:**
   - Exhibit ID: `2.1.A`
   - Выберите любой PDF/DOC файл
   - Нажмите "Загрузить"

2. **Навигация:**
   - Кликните по секции в левой панели
   - Документ автоматически прокрутится к ней

3. **Мониторинг:**
   - Следите за прогрессом в правой панели
   - Проверяйте логи агентов
   - Наблюдайте за статистикой

### Интеграция с LangGraph:
См. файл [DOCUMENT_MONITOR_INTEGRATION_GUIDE.md](DOCUMENT_MONITOR_INTEGRATION_GUIDE.md) раздел "Workflow Integration"

---

## Структура URL

- **Development:** `http://localhost:8000/index.html`
- **Production:** `http://localhost:8000/static/index.html`
- **API Docs:** `http://localhost:8000/docs`

---

## Основные команды

```bash
# Запуск development
python -m uvicorn api.main:app --reload

# Запуск production
python -m uvicorn api.main_production:app

# Запуск тестов
pytest tests/api/test_document_monitor.py -v

# Проверка API
curl http://localhost:8000/api/health
```

---

## Troubleshooting

**Проблема:** Port 8000 занят
```bash
# Используйте другой порт
python -m uvicorn api.main:app --reload --port 8080
```

**Проблема:** CORS ошибка
```python
# В core/security/config.py добавьте:
cors_allowed_origins = ["http://localhost:8000"]
```

**Проблема:** 404 Not Found
```bash
# Проверьте, что роутер подключен
python -c "from api.main import app; print('Routes:', len(app.routes))"
```

---

**Полная документация:** [DOCUMENT_MONITOR_INTEGRATION_GUIDE.md](DOCUMENT_MONITOR_INTEGRATION_GUIDE.md)
