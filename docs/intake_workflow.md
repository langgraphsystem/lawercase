# Intake Questionnaire Workflow

## Overview

The intake questionnaire is a comprehensive data collection system for immigration case management. It collects detailed life history information through an interactive Telegram bot interface with 11 themed blocks covering ~56 questions total.

**Key Features:**
- 11-block structured questionnaire (basic info → goals)
- Batch delivery (5 questions per batch)
- Database-backed progress persistence
- Type-specific validation (date, yes/no, select, list, text)
- Automatic fact synthesis for semantic memory
- Russian localization
- Inline keyboard navigation (back, pause, continue)
- Timeline extraction for temporal data

## Architecture

### Block Structure

The questionnaire is organized into 11 thematic blocks defined in `core/intake/schema.py`:

```python
INTAKE_BLOCKS = [
    IntakeBlock(id="basic_info", ...),
    IntakeBlock(id="family_childhood", ...),
    IntakeBlock(id="school", ...),
    IntakeBlock(id="university", ...),
    IntakeBlock(id="career", ...),
    IntakeBlock(id="projects_research", ...),
    IntakeBlock(id="awards", ...),
    IntakeBlock(id="talks_public_activity", ...),
    IntakeBlock(id="courses_certificates", ...),
    IntakeBlock(id="recommenders", ...),
    IntakeBlock(id="goals_usa", ...),
]
```

Each block contains:
- `id`: Unique identifier
- `title`: Russian display name (e.g., "📋 Базовая информация")
- `description`: Brief description of block content
- `questions`: List of `IntakeQuestion` objects

### Question Types

Defined in `QuestionType` enum:

| Type | Description | Validation | Example |
|------|-------------|------------|---------|
| `TEXT` | Free-form text | Length constraints (min/max) | "Как ваше полное имя?" |
| `YES_NO` | Binary choice | Recognizes да/нет/yes/no variants | "Есть ли у вас публикации?" |
| `DATE` | Date input | YYYY-MM-DD format | "Какова ваша дата рождения?" |
| `SELECT` | Single choice from options | Fuzzy matching against option list | "Какой уровень степени?" |
| `LIST` | Multiple items | Comma/newline/semicolon separated | "Перечислите ваши навыки" |

### Database Schema

Progress is stored in `mega_agent.case_intake_progress`:

```sql
CREATE TABLE case_intake_progress (
    user_id         VARCHAR(255) NOT NULL,
    case_id         VARCHAR(255) NOT NULL,
    current_block   VARCHAR(100) NOT NULL,
    current_step    INTEGER      NOT NULL DEFAULT 0,
    completed_blocks TEXT[]      NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, case_id)
);
```

**Fields:**
- `current_block`: ID of the block user is currently in (e.g., "basic_info")
- `current_step`: Question index within block (0-based)
- `completed_blocks`: Array of block IDs completed so far (e.g., `{"basic_info", "school"}`)
- Atomic updates via `INSERT ... ON CONFLICT ... DO UPDATE`

## User Flow

### 1. Starting Intake

**Trigger points:**
- User command: `/intake_start`
- Inline button: "🧾 Начать анкету" (after `/case_create`)
- Auto-resume: `/intake_resume`

**Sequence:**
1. Check active case (must have active case selected)
2. Check existing progress (resume if found)
3. Initialize progress record in database
4. Send welcome message with block overview
5. Send first batch (5 questions)

**Welcome message:**
```
🎯 **Начинаем анкетирование для кейса:** {case_title}

Я задам вам вопросы по 11 блокам (~56 вопросов).

**Блоки анкеты:**
1. 📋 Базовая информация
2. 👨‍👩‍👧‍👦 Семья и детство
3. 🎓 Школьное образование
...

💡 **Подсказки:**
• Отвечайте на каждый вопрос последовательно
• Используйте кнопки для навигации
• /intake_cancel для отмены
• /intake_status для проверки прогресса

▶️ Начнем с блока "📋 Базовая информация"
```

### 2. Batch Delivery

Questions are delivered in batches of 5 (configurable via `QUESTIONS_PER_BATCH`):

**Batch format:**
```
📦 Блок 1/11: 📋 Базовая информация
━━━━━━━━━━━━━━━━━━━━
Вопросы 1-5 из 8

1️⃣ Как ваше полное имя?
   📝 Укажите полное имя (включая отчество, если есть)

2️⃣ Какова ваша дата рождения?
   📝 Формат: ГГГГ-ММ-ДД (например, 1990-05-15)

3️⃣ Где вы родились?
...

[◀️ Назад] [⏸ Пауза] [▶️ Продолжить]
```

**Navigation buttons:**
- `◀️ Назад`: Go back to previous batch
- `⏸ Пауза`: Pause and return later
- `▶️ Продолжить`: Continue to next batch (disabled if questions unanswered)

### 3. Answer Collection

Users respond with free-form text. The system:

1. **Detects media messages** → Rejects with error
2. **Validates response** based on question type
3. **Synthesizes fact** for semantic memory
4. **Saves to memory** with tags and metadata
5. **Advances step** in progress table
6. **Checks completion**:
   - If batch complete → Send next batch
   - If block complete → Send block summary + next block
   - If all complete → Send completion message

**Validation errors** trigger retry with helpful messages:
```
❌ Некорректный формат даты. Используйте ГГГГ-ММ-ДД (например, 2023-05-15)
```

### 4. Block Completion

When all questions in a block are answered:

```
✅ Блок "📋 Базовая информация" завершен!

Прогресс: 1/11 блоков (9%)
━━━━━━━━━━━━━━━━━━━━━━━
▓▓░░░░░░░░░░░░░░░░░░░░

Переходим к следующему блоку...

📦 Блок 2/11: 👨‍👩‍👧‍👦 Семья и детство
━━━━━━━━━━━━━━━━━━━━
...
```

### 5. Questionnaire Completion

After all 11 blocks:

```
🎉 Поздравляем! Анкетирование завершено!

Вы ответили на все 56 вопросов по 11 блокам.

Ваши ответы сохранены и будут использованы для:
✓ Построения профиля кейса
✓ Генерации документов
✓ Поиска релевантной информации

Следующие шаги:
• /ask <вопрос> - Задать вопрос агенту
• /generate_letter - Создать письмо
• /case_summary - Получить краткое описание кейса

Спасибо за уделенное время! 🙏
```

## Validation

### Date Validation (`validate_date`)

**Accepted formats:**
- `YYYY-MM-DD` (primary)
- `YYYY.MM.DD`
- `YYYY/MM/DD`

**Normalization:**
- Single-digit month/day → Zero-padded (2023-5-1 → 2023-05-01)
- All separators → Hyphens

**Error message:**
```
❌ Некорректный формат даты. Используйте ГГГГ-ММ-ДД (например, 2023-05-15)
```

### Yes/No Validation (`validate_yes_no`)

**Recognized "yes" variants:**
- Russian: `да`, `конечно`, `безусловно`, `ага`, `угу`, `ок`
- English: `yes`, `y`, `ok`

**Recognized "no" variants:**
- Russian: `нет`, `не`, `никак`, `неа`
- English: `no`, `n`

**Normalization:** Returns boolean (`True`/`False`)

**Error message:**
```
❌ Пожалуйста, ответьте 'да' или 'нет'.
```

### Select Validation (`validate_select`)

**Matching strategy:**
1. Exact match (case-insensitive)
2. Option is substring of text
3. Text is substring of option

**Example:**
```python
options = ["Python", "JavaScript", "Go"]
validate_select("python", options) → (True, "Python")
validate_select("I like Python", options) → (True, "Python")
```

**Error message:**
```
❌ Некорректный выбор. Выберите один из: {options}
```

### List Parsing (`parse_list`)

**Supported separators:**
- Comma: `Python, JavaScript, Go`
- Newline: `Python\nJavaScript\nGo`
- Semicolon: `Python; JavaScript; Go`
- Mixed: `Python, JavaScript\nGo`

**Normalization:**
- Whitespace stripped
- Empty items filtered

### Text Validation (`validate_text`)

**Parameters:**
- `min_length`: Minimum character count (default: 1)
- `max_length`: Maximum character count (default: 10000)

**Error messages:**
```
❌ Текст слишком короткий. Минимум 5 символов.
❌ Текст слишком длинный. Максимум 1000 символов.
```

## Fact Synthesis

Answers are converted to declarative statements for semantic memory using `synthesize_intake_fact()`.

### Tag Prefixes

Tags from question are formatted as bracketed prefix:
```python
tags = ["intake", "career", "eb1a_criterion"]
→ "[INTAKE][career][eb1a_criterion]"
```

### Question-Specific Synthesis

50+ patterns for common questions:

| Question ID | Input | Synthesized Fact |
|-------------|-------|------------------|
| `full_name` | "Иван Петров" | `[INTAKE][basic_info] Полное имя пользователя: Иван Петров` |
| `date_of_birth` | "1990-05-15" | `[INTAKE][basic_info] Дата рождения пользователя: 1990-05-15` |
| `place_of_birth` | "Москва, Россия" | `[INTAKE][basic_info] Пользователь родился в Москва, Россия` |

### Timeline Synthesis

For school/university/career questions with timeline tags:

**Input:**
```
Question ID: school_years
Tags: ["intake", "school", "timeline"]
Answer: "2005-2016, Школа №57 в Москве"
```

**Output:**
```
[INTAKE][school][timeline] С 2005 по 2016 годы пользователь учился в школе.
Школа №57 в Москве
```

Timeline extraction includes:
- Year ranges (2005-2016, 2005–2016, с 2005 по 2016)
- Locations (cities, countries)
- Organizations (school names, universities, companies)
- Roles (job titles, positions)

### EB-1A Criterion Marking

Questions with `rationale` field get special marking:

**Input:**
```
Question ID: career_critical_role
Rationale: "Used to support EB-1A criterion: critical role."
Tags: ["intake", "career", "eb1a_criterion"]
Answer: "Да, был CTO в стартапе"
```

**Output:**
```
[INTAKE][career][eb1a_criterion] [EB-1A criterion: critical role]
Пользователь занимал критическую роль: Да, был CTO в стартапе
```

### Memory Storage

Each synthesized fact is saved as `MemoryRecord`:

```python
MemoryRecord(
    text=fact_text,              # Synthesized declarative statement
    user_id=user_id,
    type="semantic",
    case_id=case_id,
    tags=question.tags,          # ["intake", "career", "eb1a_criterion"]
    metadata={
        "source": "intake_questionnaire",
        "question_id": question.id,
        "raw_response": raw_response,
        "normalized_value": str(normalized_value),
    }
)
```

## Commands

### `/intake_start`
Start intake questionnaire for active case.

**Preconditions:**
- Active case must be selected (`/case_get <case_id>`)

**Behavior:**
- If no progress exists → Initialize and start from block 1
- If progress exists → Prompt to resume or restart

### `/intake_status`
Check current progress.

**Output:**
```
📊 Статус анкетирования

📂 Кейс: EB-1A Петров Иван
📦 Текущий блок: Карьера (5/11)
📍 Прогресс: 28/56 вопросов (50%)

✅ Завершенные блоки:
• Базовая информация
• Семья и детство
• Школьное образование
• Университет

Продолжайте, отвечая на текущие вопросы.
```

### `/intake_resume`
Resume paused questionnaire.

**Behavior:**
- Fetches progress from database
- Sends current batch of questions
- Continues from last step

### `/intake_cancel`
Cancel and delete progress.

**Behavior:**
- Deletes progress record from database
- Sends confirmation message
- User can restart anytime with `/intake_start`

## Navigation Flow

### State Machine

```
[START] → Check active case
    ↓
[INIT] → Create/load progress
    ↓
[BATCH] → Send 5 questions
    ↓
[COLLECT] → Wait for answers
    ↓ (validate)
    ├─ Invalid → Retry
    └─ Valid → Save to memory
        ↓
    [ADVANCE] → Increment step
        ↓
    [CHECK]
        ├─ Batch incomplete → [COLLECT]
        ├─ Block complete → Mark block done
        │   └─ More blocks → Next block → [BATCH]
        └─ All complete → [COMPLETE]
```

### Progress Tracking

**Database functions** (`core/storage/intake_progress.py`):

```python
# Fetch progress
progress = await get_progress(user_id, case_id)
# Returns: {current_block, current_step, completed_blocks}

# Save progress
await set_progress(user_id, case_id, block_id, step, completed)

# Advance to next question
await advance_step(user_id, case_id)

# Mark block complete
await complete_block(user_id, case_id, block_id)

# Reset (delete)
await reset_progress(user_id, case_id)
```

**Atomic updates** using `INSERT ... ON CONFLICT`:
```sql
INSERT INTO case_intake_progress (user_id, case_id, ...)
VALUES (%s, %s, ...)
ON CONFLICT (user_id, case_id)
DO UPDATE SET current_step = current_step + 1, updated_at = NOW()
```

## Integration Points

### 1. Case Handlers (`case_handlers.py`)

After case creation, inline button triggers intake:

```python
keyboard = [
    [
        InlineKeyboardButton("🧾 Начать анкету", callback_data="case_start_intake"),
        InlineKeyboardButton("⏳ Потом", callback_data="case_later"),
    ]
]
```

Callback handler:
```python
async def handle_case_callback(update, context):
    if data == "case_start_intake":
        await intake_start(update, context)
```

### 2. Memory System (`core/memory/`)

Each answer is saved to semantic memory via `MemoryManager`:

```python
await bot_context.mega_agent.memory.awrite([memory_record])
```

Facts are indexed for:
- Semantic search (embeddings)
- Tag-based filtering
- Case-specific retrieval

### 3. Agent Commands (`MegaAgent`)

Future integration for automated question generation:

```python
command = MegaAgentCommand(
    user_id=user_id,
    command_type=CommandType.INTAKE,
    action="generate_followup",
    payload={"question_id": "career_companies", "previous_answer": "..."}
)
```

## Testing

### Unit Tests (`tests/unit/intake/`)

**Coverage:**
- `test_schema.py`: Pydantic models, block structure (33 tests)
- `test_validation.py`: All validators (40 tests)
- `test_synthesis.py`: Fact synthesis patterns (18 tests)
- `test_timeline.py`: Timeline extraction (40 tests)

**Run:**
```bash
pytest tests/unit/intake/ -v
```

### Integration Tests (`tests/integration/`)

**E2E test** (`test_intake_workflow.py`):
- Create case
- Start intake
- Answer all 56 questions
- Verify progress tracking
- Verify memory records created
- Check completion

**Run:**
```bash
pytest tests/integration/test_intake_workflow.py -v
```

## Configuration

### Environment Variables

None required - uses defaults from `schema.py`.

### Customization

**Batch size** (`intake_handlers.py`):
```python
QUESTIONS_PER_BATCH = 5  # Change to 3-7 as needed
```

**Question blocks** (`core/intake/schema.py`):
- Add new blocks to `INTAKE_BLOCKS`
- Add new questions to blocks
- Ensure unique question IDs

**Validation** (`core/intake/validation.py`):
- Modify regex patterns for date formats
- Add yes/no variants for other languages
- Adjust text length constraints

**Synthesis** (`core/intake/synthesis.py`):
- Add new question_id patterns
- Customize fact templates
- Add language-specific rules

## Troubleshooting

### "Активный кейс не найден"
**Cause:** No case selected
**Solution:** `/case_get <case_id>` or `/case_create <название>`

### Questions not sending
**Cause:** Progress record corrupted
**Solution:** `/intake_cancel` then `/intake_start`

### Validation keeps failing
**Cause:** Wrong format
**Solution:** Check question hint (📝) for expected format

### Progress not saving
**Cause:** Database connection issue
**Solution:** Check `POSTGRES_DSN` in environment

## Future Enhancements

1. **Dynamic branching**: Conditional questions based on previous answers
2. **Multi-language support**: English UI option
3. **Voice input**: Transcribe voice messages
4. **Document upload**: Accept PDFs/images as answers
5. **AI-generated follow-ups**: Smart clarifying questions
6. **Progress analytics**: Time spent per block, dropout rates
7. **Export functionality**: Download answers as JSON/PDF
8. **Batch editing**: Review and edit previous answers

## References

- **Schema definition**: `core/intake/schema.py`
- **Validation logic**: `core/intake/validation.py`
- **Fact synthesis**: `core/intake/synthesis.py`
- **Timeline extraction**: `core/intake/timeline.py`
- **Handler implementation**: `telegram_interface/handlers/intake_handlers.py`
- **Progress storage**: `core/storage/intake_progress.py`
- **Database migration**: `migrations/003_case_intake_progress.sql`
