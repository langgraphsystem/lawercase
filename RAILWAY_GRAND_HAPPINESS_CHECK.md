# Railway Project "grand-happiness" - Comprehensive Check Guide

## Дата проверки: 31 октября 2025

---

## 1. Подключение к проекту

### Метод 1: Railway CLI (Интерактивный)

```bash
# Подключиться к проекту
railway link

# Выбрать:
# 1. Workspace: langgraphsystem's Projects
# 2. Project: grand-happiness

# Проверить подключение
railway status
```

### Метод 2: Railway Dashboard (Веб-интерфейс)

```
1. Зайти на https://railway.app/dashboard
2. Выбрать Workspace: langgraphsystem
3. Открыть проект: grand-happiness
4. Перейти в Settings → Variables
```

---

## 2. Проверка Environment Variables (API ключи)

### Обязательные переменные для Telegram Bot:

```bash
# После railway link:
railway variables

# Или через dashboard: Settings → Variables
```

### Список необходимых переменных:

| Переменная | Описание | Обязательность | Пример значения |
|------------|----------|----------------|-----------------|
| **TELEGRAM_BOT_TOKEN** | Telegram Bot API token | ✅ Критично | `7472625853:AAGPl30...` |
| **OPENAI_API_KEY** | OpenAI API ключ | ✅ Критично | `sk-proj-...` |
| **ANTHROPIC_API_KEY** | Anthropic Claude API | ⚠️ Рекомендуется | `sk-ant-...` |
| **GEMINI_API_KEY** | Google Gemini API | ⚠️ Опционально | `AI...` |
| **DATABASE_URL** | PostgreSQL connection | ⚠️ Опционально | `postgresql://...` |
| **REDIS_URL** | Redis connection | ⚠️ Опционально | `redis://...` |
| **PINECONE_API_KEY** | Vector DB ключ | ⚠️ Опционально | `...` |
| **PINECONE_ENVIRONMENT** | Pinecone окружение | ⚠️ Опционально | `us-east-1-aws` |

### Команды для проверки:

```bash
# Проверить конкретную переменную
railway variables | grep TELEGRAM_BOT_TOKEN
railway variables | grep OPENAI_API_KEY
railway variables | grep ANTHROPIC_API_KEY

# Проверить все переменные
railway variables > railway_env_vars.txt
cat railway_env_vars.txt
```

### ⚠️ Безопасность:
- НЕ коммитить файл с переменными в Git
- НЕ отправлять значения в открытом виде
- Проверять только наличие переменных, а не их значения

---

## 3. Проверка статуса deployment

### Текущий деплоймент:

```bash
# Статус сервиса
railway status

# Список последних деплойментов
railway deployments

# Информация о текущем билде
railway build logs
```

### Что проверять:

1. **Статус**: `DEPLOYED` ✅ или `FAILED` ❌
2. **Версия кода**: Commit hash (должен быть 984ffc6 или новее)
3. **Build время**: Когда последний раз деплоился
4. **Health check**: Проходит ли health check

### Команда для полной информации:

```bash
# Получить всю информацию о проекте
railway service
railway environment
railway status -v
```

---

## 4. Проверка логов бота

### Получить последние логи:

```bash
# Последние 50 строк
railway logs --tail 50

# Последние 100 строк
railway logs --tail 100

# Логи в реальном времени (live tail)
railway logs --follow

# Логи за последний час
railway logs --since 1h
```

### Что искать в логах:

#### ✅ Признаки успешного запуска:

```json
{"event": "telegram.bot.starting", "level": "info"}
{"event": "telegram.bot.running", "level": "info"}
HTTP Request: POST https://api.telegram.org/.../getMe "HTTP/1.1 200 OK"
```

#### ❌ Признаки проблем (СТАРЫЙ код):

```
[INFO] event="telegram.bot.starting"  # ← Старый формат (не JSON)
RuntimeError: This event loop is already running
AttributeError: 'RBACManager' object has no attribute 'check_permission'
AttributeError: 'PromptInjectionDetector' object has no attribute 'analyze'
```

#### ✅ Признаки НОВОГО кода (после fixes):

```json
{"event": "telegram.bot.starting", "level": "info"}  # ← JSON формат
{"event": "telegram.bot.running", "level": "info"}
{"event": "telegram.ask.processing", "question_length": 14}
{"event": "telegram.ask.command_created"}
```

### Команды для анализа:

```bash
# Проверить формат логов (JSON vs старый)
railway logs --tail 20 | grep "event=" | head -5

# Найти ошибки
railway logs --tail 100 | grep -i "error"
railway logs --tail 100 | grep -i "exception"

# Проверить версию кода в билде
railway logs --tail 200 | grep -i "commit\|version"
```

---

## 5. Тестирование команд бота

### 5.1. Базовые команды

#### /start
```
Отправить: /start
Ожидается: Welcome message с описанием бота
```

**Лог должен показать**:
```json
{"event": "telegram.start.received", "user_id": ...}
{"event": "telegram.start.sent"}
```

#### /help
```
Отправить: /help
Ожидается: Список всех доступных команд
```

**Лог должен показать**:
```json
{"event": "telegram.help_command.received"}
{"event": "telegram.help_command.sent"}
```

### 5.2. Команды с валидацией

#### /ask (без аргументов)
```
Отправить: /ask
Ожидается: "Please provide a question after /ask"
```

**Лог должен показать**:
```json
{"event": "telegram.ask.received"}
{"event": "telegram.ask.no_args", "level": "warning"}
```

### 5.3. Команды с MegaAgent

#### /ask What is EB-1A?
```
Отправить: /ask What is EB-1A?
Ожидается: Ответ от MegaAgent (или ошибка если backend не настроен)
```

**Логи (SUCCESS - новый код)**:
```json
{"event": "telegram.ask.received"}
{"event": "telegram.ask.processing", "question_length": 14}
{"event": "telegram.ask.command_created", "command_id": "..."}
{"event": "telegram.ask.response_received"}
```

**Логи (FAIL - старый код)**:
```json
{"error": "'RBACManager' object has no attribute 'check_permission'"}
```

**Логи (FAIL - новый код, backend issue)**:
```json
{"error": "'dict' object has no attribute 'thread_id'"}
```

#### /case_get <case_id>
```
Отправить: /case_get 12345
Ожидается: Case information или ошибка если case не найден
```

#### /memory_lookup <query>
```
Отправить: /memory_lookup immigration law
Ожидается: Semantic search results
```

#### /generate_letter <title>
```
Отправить: /generate_letter Reference Letter
Ожидается: Generated document или template
```

### 5.4. Admin команды (если доступны)

#### /chat <prompt>
```
Отправить: /chat Hello, how are you?
Ожидается: Direct GPT response (если handler реализован)
```

#### /models
```
Отправить: /models
Ожидается: List of available OpenAI models (если handler реализован)
```

---

## 6. Проверка версии кода

### Команды для определения версии:

```bash
# Проверить commit hash в билде
railway logs --tail 500 | grep -i "commit"

# Проверить дату последнего деплоймента
railway deployments | head -5

# Сравнить с GitHub
git log --oneline -5
```

### Ожидаемая версия кода:

**GitHub branch**: `hardening/roadmap-v1`
**Latest commit**: `984ffc6` (или новее)
**Commit message**: "docs: Add comprehensive final status report..."

### Признаки актуальной версии:

1. ✅ Логи в JSON формате
2. ✅ Нет ошибок "event loop already running"
3. ✅ Нет ошибок "check_permission"
4. ✅ Нет ошибок "analyze" (PromptInjection)
5. ✅ Нет ошибок "blocked" attribute

### Признаки старой версии:

1. ❌ Логи в формате `[INFO] event=...`
2. ❌ RuntimeError: event loop
3. ❌ AttributeError: check_permission
4. ❌ AttributeError: analyze

---

## 7. Redeploy (если нужно)

### Когда нужен redeploy:

- ⚠️ Бот показывает старые ошибки
- ⚠️ Логи не в JSON формате
- ⚠️ Commit hash не соответствует GitHub
- ⚠️ После пуша нового кода в GitHub

### Метод 1: Railway CLI

```bash
# Убедиться что подключены к grand-happiness
railway status

# Сделать redeploy
railway up

# Или принудительный redeploy
railway redeploy
```

### Метод 2: Railway Dashboard

```
1. Открыть https://railway.app/dashboard
2. Выбрать grand-happiness
3. Найти bot service
4. Нажать "Deploy Latest"или "Redeploy"
5. Дождаться завершения билда (3-5 минут)
```

### Метод 3: Git Push (auto-deploy)

```bash
# Убедиться что на правильной ветке
git branch --show-current  # hardening/roadmap-v1

# Пушнуть изменения
git push origin hardening/roadmap-v1

# Railway должен автоматически задеплоить
# Проверить через несколько минут
railway logs --tail 50
```

---

## 8. Health Check Commands

### Quick check (все в одном)

```bash
# Создать скрипт для быстрой проверки
cat > railway_health_check.sh << 'EOF'
#!/bin/bash
echo "=== Railway grand-happiness Health Check ==="
echo ""
echo "1. Project Status:"
railway status
echo ""
echo "2. Environment Variables (count):"
railway variables | wc -l
echo ""
echo "3. Recent Deployments:"
railway deployments | head -3
echo ""
echo "4. Latest Logs (last 20 lines):"
railway logs --tail 20
echo ""
echo "5. Error Check (last 100 lines):"
railway logs --tail 100 | grep -i "error\|exception" | tail -10
echo ""
echo "=== Health Check Complete ==="
EOF

chmod +x railway_health_check.sh
./railway_health_check.sh
```

---

## 9. Checklist полной проверки

### Предварительные шаги:
- [ ] Railway CLI установлен и аутентифицирован (`railway whoami`)
- [ ] Git репозиторий на latest commit (`git pull`)
- [ ] Доступ к Telegram боту (@lawercasebot)

### Проверка конфигурации:
- [ ] Подключен к проекту `grand-happiness` (`railway link`)
- [ ] TELEGRAM_BOT_TOKEN установлен
- [ ] OPENAI_API_KEY установлен
- [ ] ANTHROPIC_API_KEY установлен (опционально)
- [ ] Другие ключи настроены по необходимости

### Проверка деплоймента:
- [ ] Статус: DEPLOYED
- [ ] Commit hash: 984ffc6 или новее
- [ ] Build успешный (нет ошибок)
- [ ] Health check проходит

### Проверка логов:
- [ ] Формат логов: JSON ✅ (не `[INFO] event=...` ❌)
- [ ] Событие: `telegram.bot.starting`
- [ ] Событие: `telegram.bot.running`
- [ ] HTTP 200 OK для Telegram API
- [ ] Нет event loop errors
- [ ] Нет RBAC errors
- [ ] Нет PromptInjection errors

### Тестирование команд:
- [ ] `/start` работает
- [ ] `/help` работает
- [ ] `/ask` (без аргументов) показывает валидацию
- [ ] `/ask What is EB-1A?` создает command
- [ ] `/case_get` тестируется
- [ ] `/memory_lookup` тестируется
- [ ] `/generate_letter` тестируется

### Финальная проверка:
- [ ] Бот отвечает на все команды
- [ ] Логи показывают успешную обработку
- [ ] Нет критических ошибок
- [ ] Производительность приемлемая

---

## 10. Ожидаемые результаты

### ✅ Идеальный статус:

```bash
# railway status
Project: grand-happiness
Environment: production
Status: DEPLOYED
Health: HEALTHY
Commit: 984ffc6
```

```bash
# railway logs --tail 20
{"event": "telegram.bot.starting", "level": "info"}
{"event": "telegram.bot.running", "level": "info"}
{"event": "telegram.help_command.received"}
{"event": "telegram.help_command.sent"}
{"event": "telegram.ask.processing"}
{"event": "telegram.ask.command_created"}
```

### ⚠️ Проблемный статус:

```bash
# railway status
Status: FAILED
```

```bash
# railway logs --tail 20
[INFO] event="telegram.bot.starting"  # ← Старый формат
RuntimeError: This event loop is already running
AttributeError: 'RBACManager' object has no attribute 'check_permission'
```

**Решение**: Сделать redeploy (`railway up`)

---

## 11. Troubleshooting

### Проблема 1: Bot не отвечает на команды

**Проверить**:
```bash
railway logs --tail 100 | grep "telegram.bot"
railway variables | grep TELEGRAM_BOT_TOKEN
```

**Решения**:
1. Проверить TELEGRAM_BOT_TOKEN
2. Проверить что бот запущен (логи)
3. Сделать redeploy

### Проблема 2: Старый формат логов

**Симптомы**: `[INFO] event=...` вместо JSON

**Решение**:
```bash
railway up  # Redeploy latest code
```

### Проблема 3: RBAC/PromptInjection errors

**Симптомы**: AttributeError на check_permission или analyze

**Решение**: Код устаревший, нужен redeploy
```bash
railway up
```

### Проблема 4: thread_id error

**Симптомы**: `'dict' object has no attribute 'thread_id'`

**Статус**: Это НОВАЯ ошибка (код актуальный, backend issue)

**Решение**: Backend service configuration (database, memory manager)

---

## 12. Следующие шаги после проверки

### Если всё работает ✅:
1. Протестировать все команды end-to-end
2. Настроить backend services (database, vector store)
3. Мониторинг и метрики

### Если нужен redeploy ⚠️:
1. Сделать `railway up`
2. Дождаться завершения билда
3. Проверить логи снова
4. Протестировать команды

### Если не хватает переменных ❌:
1. Добавить через dashboard или CLI
2. Сделать redeploy
3. Проверить что бот запустился

---

## Контакты

**Railway Account**: brotherslyft@gmail.com
**GitHub**: https://github.com/langgraphsystem/lawercase
**Branch**: hardening/roadmap-v1
**Bot**: @lawercasebot (ID: 7472625853)

**Документация проекта**:
- [FINAL_STATUS_2025-10-31.md](FINAL_STATUS_2025-10-31.md)
- [RAILWAY_DEPLOYMENT_STATUS.md](RAILWAY_DEPLOYMENT_STATUS.md)
- [BOT_TESTING_RESULTS_2025-10-31.md](BOT_TESTING_RESULTS_2025-10-31.md)

---

**Дата создания**: 31 октября 2025
**Статус**: Ready for grand-happiness check
