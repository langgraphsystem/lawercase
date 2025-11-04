# 🇺🇸 EB-1A Petition Workflow - Complete Guide

## Оглавление

1. [Введение](#введение)
2. [Что такое EB-1A](#что-такое-eb-1a)
3. [Архитектура системы](#архитектура-системы)
4. [Полный цикл обработки](#полный-цикл-обработки)
5. [API Reference](#api-reference)
6. [Примеры использования](#примеры-использования)
7. [Интеграция с ботами](#интеграция-с-ботами)

---

## Введение

EB-1A (Employment-Based First Preference - Extraordinary Ability) - это категория американской иммиграционной визы для людей с экстраординарными способностями в науке, искусстве, образовании, бизнесе или спорте.

**Наша система автоматизирует:**
- ✅ Сбор данных через интерактивный опросник
- ✅ Оценку соответствия 10 критериям USCIS
- ✅ Генерацию необходимых документов
- ✅ Отслеживание прогресса петиции

---

## Что такое EB-1A

### 10 Критериев USCIS (8 CFR 204.5(h)(3))

Для подачи петиции EB-1A необходимо соответствовать **минимум 3 из 10 критериев**:

| # | Критерий | Описание | Примеры доказательств |
|---|----------|----------|----------------------|
| 1 | **Awards** | Национальные/международные премии | Нобелевская премия, Turing Award, Grammy |
| 2 | **Membership** | Членство в ассоциациях с высокими требованиями | ACM Fellow, IEEE Fellow, National Academy |
| 3 | **Press** | Публикации о вас в СМИ | NY Times, MIT Technology Review, Wired |
| 4 | **Judging** | Судейство работ других | Рецензирование статей, оценка грантов NSF |
| 5 | **Contribution** | Оригинальный вклад большой важности | Изобретения, патенты, новые методологии |
| 6 | **Scholarly** | Научные публикации | Статьи в Nature, Science, top conferences |
| 7 | **Exhibition** | Выставки работ | MoMA, Guggenheim (для искусства) |
| 8 | **Leadership** | Лидерские роли в организациях | CTO Google, Director MIT AI Lab |
| 9 | **Salary** | Высокая зарплата (топ 10%) | $300k+ для AI/ML, $200k+ для academia |
| 10 | **Commercial** | Коммерческий успех в искусстве | Box office, Grammy sales (для артистов) |

---

## Архитектура Системы

### Компоненты

```
┌──────────────────────────────────────────────────────────┐
│                    Telegram/Web Bot                      │
│          (Пользователь начинает диалог)                  │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│             POST /v1/eb1/create                          │
│             POST /v1/eb1/message                         │
│             GET  /v1/eb1/status                          │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│                     MegaAgent                            │
│         (Центральный оркестратор)                        │
│                                                          │
│  - RBAC проверка                                         │
│  - Prompt injection detection                            │
│  - Audit trail                                           │
│  - Маршрутизация к EB1Agent                             │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│                      EB1Agent                            │
│        (Интерактивный conversational agent)              │
│                                                          │
│  📋 Questionnaire Engine:                                │
│     - 40+ вопросов по 10 критериям                       │
│     - Валидация ответов                                  │
│     - Динамическая навигация                             │
│                                                          │
│  📊 Evaluation Engine:                                   │
│     - Подсчет критериев (нужно ≥3)                       │
│     - Оценка силы доказательств                          │
│     - Eligibility score (0-100%)                         │
│                                                          │
│  💾 State Management:                                    │
│     - EB1PetitionData (structured data)                  │
│     - EB1ConversationState (dialog state)                │
│     - EB1CriterionEvidence (criteria evidence)           │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│                   MemoryManager                          │
│                                                          │
│  📝 Episodic Store:                                      │
│     - Полный лог диалога                                 │
│     - Audit events                                       │
│                                                          │
│  🧠 Semantic Store:                                      │
│     - Факты о петиции                                    │
│     - Evidence с embeddings                              │
│     - Семантический поиск                                │
│                                                          │
│  💭 Working Memory (RMT):                                │
│     - Текущий контекст                                   │
│     - Персона пользователя                               │
└──────────────────────────────────────────────────────────┘
```

### Модели Данных

#### EB1PetitionData
```python
{
    "petition_id": "eb1_a3f8b2c14567",
    "user_id": "user123",
    "status": "READY_FOR_FILING",  # DRAFT | DATA_COLLECTION | READY_FOR_FILING
    "current_step": "REVIEW_SUMMARY",

    # Персональная информация
    "personal_info": {
        "full_name": "John Smith",
        "email": "john@example.com",
        "current_country": "Russia",
        "current_visa_status": "H-1B"
    },

    # Область экспертизы
    "field_of_expertise": {
        "field": "Artificial Intelligence",
        "years_of_experience": 15,
        "current_position": "Lead AI Researcher",
        "education_level": "PhD in Computer Science"
    },

    # Доказательства по критериям
    "criteria_evidence": {
        "awards": {
            "criterion": "awards",
            "met": true,
            "evidence_count": 2,
            "evidence_items": [
                {"description": "Best Paper Award IEEE 2023"},
                {"description": "Google AI Research Award 2022"}
            ],
            "strength_score": 0.85
        },
        // ... остальные 9 критериев
    },

    # Результаты оценки
    "criteria_met_count": 7,  // Выполнено 7 из 10 критериев
    "eligibility_score": 0.85,  // 85% - высокая вероятность одобрения
    "recommendation": "✅ РЕКОМЕНДУЕТСЯ подавать петицию EB-1A",

    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-15T10:45:00Z",
    "completed_at": "2025-01-15T10:45:00Z"
}
```

---

## Полный Цикл Обработки

### Сценарий: Пользователь создает EB-1A петицию в Telegram боте

#### **Этап 1: Инициализация** (0-5 секунд)

```
USER: /start_eb1
```

**Что происходит:**

1. **Telegram Bot** → FastAPI
   ```
   POST /v1/eb1/create
   {
     "user_id": "tg_123456789"
   }
   ```

2. **FastAPI** → MegaAgent
   ```python
   cmd = MegaAgentCommand(
       user_id="tg_123456789",
       command_type=CommandType.EB1,
       action="create",
       payload={}
   )
   response = await mega_agent.handle_command(cmd, UserRole.CLIENT)
   ```

3. **MegaAgent** → EB1Agent
   ```python
   # Создание петиции и conversation state
   petition, welcome_msg = await eb1_agent.create_petition(user_id)

   # petition_id: "eb1_a3f8b2c14567"
   # status: "DATA_COLLECTION"
   # current_step: "PERSONAL_INFO"
   ```

4. **EB1Agent** → MemoryManager
   ```python
   # Сохранение в Episodic память
   await memory.alog_audit(AuditEvent(
       action="create_eb1_petition",
       payload={"petition_id": petition_id}
   ))

   # Сохранение в Semantic память
   await memory.awrite(MemoryRecord(
       text="EB-1A Petition created",
       metadata={"petition_id": petition_id}
   ))
   ```

**Ответ пользователю:**
```
🇺🇸 СОЗДАНИЕ ПЕТИЦИИ EB-1A
================================================

Добро пожаловать в процесс подготовки петиции EB-1A!

EB-1A - это виза для людей с экстраординарными способностями
в науке, искусстве, образовании, бизнесе или спорте.

📋 Я задам вам вопросы по 10 критериям USCIS.
✅ Для подачи нужно соответствовать минимум 3 из 10 критериев.
⏱️ Процесс займет 15-30 минут.

🆔 ID вашей петиции: eb1_a3f8b2c14567

Начнем с персональной информации:

❓ Как ваше полное имя (как в паспорте)?
```

---

#### **Этап 2: Интерактивный Опрос** (5-30 минут)

**Вопрос-Ответ Loop:**

```
USER: John Smith

BOT: ✅ Записано: John Smith

    ❓ Ваш email адрес?
```

**Что происходит при каждом сообщении:**

1. **Telegram Bot** → FastAPI
   ```
   POST /v1/eb1/message
   {
     "petition_id": "eb1_a3f8b2c14567",
     "message": "John Smith"
   }
   ```

2. **MegaAgent** → EB1Agent
   ```python
   bot_response = await eb1_agent.process_user_message(
       petition_id="eb1_a3f8b2c14567",
       user_message="John Smith",
       user_id="tg_123456789"
   )
   ```

3. **EB1Agent**: Обработка ответа
   ```python
   # 1. Получение текущего вопроса
   question = self._get_question_by_id(current_question_id)

   # 2. Валидация ответа
   validation = self._validate_answer(question, "John Smith")
   # Result: {"valid": True, "parsed_value": "John Smith"}

   # 3. Сохранение ответа
   answer = EB1Answer(
       question_id="personal_full_name",
       answer="John Smith",
       answered_at=datetime.utcnow()
   )
   conversation.answers["personal_full_name"] = answer

   # 4. Обновление petition data
   petition.personal_info.full_name = "John Smith"

   # 5. Получение следующего вопроса
   next_q = await self.get_next_question(petition_id)
   ```

4. **MemoryManager**: Сохранение взаимодействия
   ```python
   await memory.awrite(MemoryRecord(
       text="EB1 Q&A - User: John Smith... Bot: Записано...",
       metadata={"petition_id": petition_id}
   ))
   ```

**Типы вопросов:**

| Тип | Валидация | Пример |
|-----|-----------|--------|
| `yes_no` | да/нет, yes/no | "Получали ли вы награды?" |
| `text` | минимальная длина, email format | "Ваш email?" |
| `number` | min/max диапазон | "Сколько публикаций?" |
| `list` | разделение по запятым/переносам | "Перечислите награды" |

**Навигация по этапам:**

```
PERSONAL_INFO (4 вопроса)
    ↓
FIELD_OF_EXPERTISE (4 вопроса)
    ↓
CRITERION_AWARDS (2 вопроса)
    ↓
CRITERION_MEMBERSHIP (2 вопроса)
    ↓
CRITERION_PRESS (2 вопроса)
    ↓
CRITERION_JUDGING (2 вопроса)
    ↓
CRITERION_CONTRIBUTION (2 вопроса)
    ↓
CRITERION_SCHOLARLY (3 вопроса)
    ↓
CRITERION_EXHIBITION (1 вопрос)
    ↓
CRITERION_LEADERSHIP (2 вопроса)
    ↓
CRITERION_SALARY (2 вопроса)
    ↓
CRITERION_COMMERCIAL (1 вопрос)
    ↓
REVIEW_SUMMARY
```

---

#### **Этап 3: Итоговая Оценка** (30 секунд)

После всех вопросов система генерирует итоговую сводку:

```python
async def _generate_criteria_summary(petition, conversation):
    # Подсчет критериев
    met_criteria = [c for c in EB1Criterion
                    if petition.criteria_evidence[c.value].met]

    petition.criteria_met_count = len(met_criteria)

    # Оценка eligibility
    if len(met_criteria) >= 3:
        petition.eligibility_score = min(1.0, len(met_criteria)/10.0 + 0.3)
        petition.recommendation = "✅ РЕКОМЕНДУЕТСЯ подавать петицию"
        petition.status = EB1PetitionStatus.READY_FOR_FILING
    else:
        petition.eligibility_score = len(met_criteria)/10.0
        petition.recommendation = "⚠️ Недостаточно критериев"
        petition.status = EB1PetitionStatus.CRITERIA_REVIEW
```

**Ответ пользователю:**

```
📊 ИТОГОВАЯ ОЦЕНКА СООТВЕТСТВИЯ EB-1A
================================================

✅ Соответствует критериям: 7/10
📈 Оценка: 85%
💡 ✅ РЕКОМЕНДУЕТСЯ подавать петицию EB-1A

✅ Выполненные критерии:
  1. Awards (сила: 85%)
  2. Membership (сила: 80%)
  3. Press (сила: 75%)
  4. Judging (сила: 70%)
  5. Contribution (сила: 90%)
  6. Scholarly (сила: 95%)
  7. Leadership (сила: 85%)

❌ Не выполненные критерии:
  - Exhibition
  - Salary
  - Commercial

================================================

🎉 Отлично! Вы соответствуете минимальным требованиям для EB-1A.
Хотите, чтобы я подготовил документы для подачи? (да/нет)
```

---

#### **Этап 4: Проверка Статуса**

В любой момент пользователь может проверить статус:

```
USER: /status eb1_a3f8b2c14567
```

**API Call:**
```
GET /v1/eb1/status?petition_id=eb1_a3f8b2c14567
```

**Ответ:**
```json
{
  "petition_id": "eb1_a3f8b2c14567",
  "status": "READY_FOR_FILING",
  "current_step": "REVIEW_SUMMARY",
  "criteria_met": 7,
  "eligibility_score": 0.85,
  "recommendation": "✅ РЕКОМЕНДУЕТСЯ подавать петицию EB-1A",
  "completed_steps": 12,
  "total_questions_answered": 35
}
```

---

## API Reference

### 1. Создание Петиции

**Endpoint:** `POST /v1/eb1/create`

**Request:**
```json
{
  "user_id": "user123"
}
```

**Response:**
```json
{
  "operation": "create_eb1_petition",
  "petition_id": "eb1_a3f8b2c14567",
  "status": "data_collection",
  "message": "🇺🇸 СОЗДАНИЕ ПЕТИЦИИ EB-1A...",
  "awaiting_input": true
}
```

### 2. Отправка Сообщения

**Endpoint:** `POST /v1/eb1/message`

**Request:**
```json
{
  "petition_id": "eb1_a3f8b2c14567",
  "message": "John Smith"
}
```

**Response:**
```json
{
  "operation": "eb1_message",
  "petition_id": "eb1_a3f8b2c14567",
  "bot_response": "✅ Записано: John Smith\n\n❓ Ваш email адрес?",
  "awaiting_input": true
}
```

### 3. Получение Статуса

**Endpoint:** `GET /v1/eb1/status?petition_id={petition_id}`

**Response:**
```json
{
  "petition_id": "eb1_a3f8b2c14567",
  "status": "ready_for_filing",
  "criteria_met": 7,
  "eligibility_score": 0.85,
  "recommendation": "✅ РЕКОМЕНДУЕТСЯ подавать петицию"
}
```

### 4. Получение Полных Данных

**Endpoint:** `GET /v1/eb1/get?petition_id={petition_id}`

**Response:**
```json
{
  "operation": "get_eb1_petition",
  "petition": {
    "petition_id": "eb1_a3f8b2c14567",
    "personal_info": {...},
    "field_of_expertise": {...},
    "criteria_evidence": {...},
    "criteria_met_count": 7,
    "eligibility_score": 0.85
  }
}
```

---

## Примеры Использования

### Python SDK

```python
from core.groupagents.mega_agent import MegaAgent, MegaAgentCommand, CommandType, UserRole

async def create_eb1_petition():
    agent = MegaAgent()

    # Создание петиции
    cmd = MegaAgentCommand(
        user_id="user123",
        command_type=CommandType.EB1,
        action="create",
        payload={}
    )

    response = await agent.handle_command(cmd, UserRole.LAWYER)
    petition_id = response.result["petition_id"]
    print(response.result["message"])

    # Отправка ответа
    cmd = MegaAgentCommand(
        user_id="user123",
        command_type=CommandType.EB1,
        action="message",
        payload={
            "petition_id": petition_id,
            "message": "John Smith"
        }
    )

    response = await agent.handle_command(cmd, UserRole.LAWYER)
    print(response.result["bot_response"])
```

### curl

```bash
# Создание петиции
curl -X POST http://localhost:8000/v1/eb1/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'

# Отправка сообщения
curl -X POST http://localhost:8000/v1/eb1/message \
  -H "Content-Type: application/json" \
  -d '{
    "petition_id": "eb1_a3f8b2c14567",
    "message": "John Smith"
  }'

# Получение статуса
curl http://localhost:8000/v1/eb1/status?petition_id=eb1_a3f8b2c14567
```

---

## Интеграция с Ботами

### Telegram Bot (aiogram)

```python
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import httpx

bot = Bot(token="YOUR_BOT_TOKEN")
dp = Dispatcher()

# Хранилище petition_id для каждого пользователя
user_petitions = {}

@dp.message(Command("start_eb1"))
async def start_eb1(message: types.Message):
    user_id = f"tg_{message.from_user.id}"

    # Создание петиции через API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/eb1/create",
            json={"user_id": user_id}
        )
        data = response.json()

    # Сохранение petition_id
    user_petitions[message.from_user.id] = data["petition_id"]

    # Отправка приветственного сообщения
    await message.answer(data["message"])

@dp.message()
async def handle_message(message: types.Message):
    user_id = f"tg_{message.from_user.id}"
    petition_id = user_petitions.get(message.from_user.id)

    if not petition_id:
        await message.answer("Используйте /start_eb1 для начала")
        return

    # Отправка сообщения в систему
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/eb1/message",
            json={
                "petition_id": petition_id,
                "message": message.text
            }
        )
        data = response.json()

    # Отправка ответа бота
    await message.answer(data["bot_response"])

if __name__ == "__main__":
    dp.run_polling(bot)
```

---

## Метрики и Мониторинг

Система собирает метрики на каждом этапе:

```python
{
    "petition_id": "eb1_a3f8b2c14567",
    "total_time": "25min",
    "breakdown": {
        "petition_creation": "2s",
        "questionnaire": "23min",
        "evaluation": "5s",
        "memory_operations": "5s"
    },
    "questions_answered": 35,
    "criteria_met": 7,
    "memory_operations": {
        "episodic_writes": 40,
        "semantic_writes": 12,
        "embeddings_generated": 8
    },
    "audit_events": 45
}
```

---

## Безопасность

### RBAC Проверки

```python
# Для создания петиции нужна роль LAWYER или выше
ROLE_PERMISSIONS = {
    UserRole.CLIENT: [Permission.READ_CASE],  # Только просмотр
    UserRole.LAWYER: [Permission.CREATE_CASE, Permission.GENERATE_DOCUMENT],
    UserRole.ADMIN: [Permission.ADMIN_ACCESS, ...]
}
```

### Prompt Injection Detection

```python
# Автоматическая проверка всех сообщений пользователя
if self.prompt_detector:
    result = self.prompt_detector.analyze(user_message)
    if result.blocked:
        raise CommandError("Обнаружена попытка инъекции")
```

### Audit Trail

Все операции логируются в immutable audit trail:

```python
{
    "event_id": "evt_001",
    "timestamp": "2025-01-15T10:30:00Z",
    "user_id": "user123",
    "action": "create_eb1_petition",
    "petition_id": "eb1_a3f8b2c14567",
    "prev_hash": "abc123..."  # Blockchain-like chain
}
```

---

## Расширение Системы

### Добавление Новых Вопросов

```python
# В eb1_models.py
EB1_QUESTIONNAIRE_TEMPLATES[EB1QuestionnaireStep.CRITERION_AWARDS].append(
    EB1Question(
        question_id="awards_international",
        step=EB1QuestionnaireStep.CRITERION_AWARDS,
        criterion=EB1Criterion.AWARDS,
        question_text="Были ли награды международными?",
        question_type="yes_no",
        required=False
    )
)
```

### Добавление Генерации Документов

```python
# В EB1Agent
async def generate_i140_form(self, petition_id: str) -> str:
    """Генерация формы I-140 из данных петиции"""
    petition = self._petitions[petition_id]

    # Формирование PDF с использованием данных petition
    template = load_template("i140_template.pdf")
    filled_pdf = fill_template(template, petition.model_dump())

    return save_pdf(filled_pdf)
```

---

## FAQ

**Q: Сколько времени занимает опросник?**
A: В среднем 15-30 минут, в зависимости от количества доказательств.

**Q: Можно ли сохранить прогресс и вернуться позже?**
A: Да, petition_id сохраняется, можно продолжить в любое время.

**Q: Что если пользователь не соответствует 3 критериям?**
A: Система даст рекомендации по сбору дополнительных доказательств.

**Q: Генерируются ли документы автоматически?**
A: В текущей версии - подготовка к генерации. Следующая версия включит автогенерацию I-140, Cover Letter, Evidence Lists.

---

## Поддержка

- 📧 Email: support@example.com
- 💬 Telegram: @eb1_support_bot
- 📚 Docs: https://docs.example.com/eb1

---

**Версия:** 1.0.0
**Дата:** January 2025
**Лицензия:** Proprietary
