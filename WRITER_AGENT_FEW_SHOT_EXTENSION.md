# WriterAgent Few-Shot Learning Extension

## Обзор

Расширение WriterAgent добавляет мощный функционал few-shot learning для генерации юридических секций EB-1A петиций. Система использует библиотеку успешных примеров и структурных паттернов для создания высококачественного профессионального контента.

## Основные Компоненты

### 1. **FewShotExample** - Модель Примера

Хранит успешные примеры написания секций для обучения системы:

```python
class FewShotExample:
    example_id: str              # Уникальный ID примера
    section_type: str            # Тип секции (awards, press, judging, etc.)
    criterion_name: str          # Название критерия EB-1A
    input_data: Dict[str, Any]   # Входные данные (evidence, beneficiary info)
    generated_content: str       # Высококачественный сгенерированный контент
    quality_score: float         # Оценка качества (0.0-1.0)
    metadata: Dict[str, Any]     # Дополнительные метаданные
    tags: List[str]              # Теги для фильтрации
    usage_count: int             # Счётчик использования
```

**Пример создания:**

```python
example = FewShotExample(
    section_type="awards",
    criterion_name="Awards and Prizes",
    input_data={
        "beneficiary": "Dr. Jane Smith",
        "field": "Artificial Intelligence",
        "awards": [{"title": "Best Paper Award", "organization": "IEEE"}]
    },
    generated_content="...",  # Полный текст примера
    quality_score=0.9,
    tags=["awards", "peer-reviewed", "international"]
)
```

### 2. **SectionPattern** - Структурный Паттерн

Определяет переиспользуемые структуры и фразы для юридической аргументации:

```python
class SectionPattern:
    pattern_id: str                    # Уникальный ID
    pattern_type: str                  # opening, evidence_analysis, conclusion
    section_types: List[str]           # Применимые типы секций
    template_structure: str            # Шаблон структуры с переменными
    example_phrases: List[str]         # Примеры профессиональных фраз
    legal_language_hints: List[str]    # Юридические формулировки
    variables: List[str]               # Переменные для подстановки
```

**Типы паттернов:**

- **opening** - Вступительная часть секции
- **evidence_analysis** - Анализ доказательств
- **conclusion** - Заключение с юридическими ссылками
- **comparative_analysis** - Сравнительный анализ

### 3. **GeneratedSection** - Результат Генерации

Содержит сгенерированную секцию с метаданными:

```python
class GeneratedSection:
    section_id: str                    # Уникальный ID секции
    section_type: str                  # Тип секции
    title: str                         # Заголовок
    content: str                       # Сгенерированный контент
    evidence_used: List[str]           # Использованные доказательства
    examples_used: List[str]           # ID использованных примеров
    patterns_applied: List[str]        # Применённые паттерны
    confidence_score: float            # Оценка уверенности (0.0-1.0)
    word_count: int                    # Количество слов
    suggestions: List[str]             # Предложения по улучшению
    metadata: Dict[str, Any]           # Дополнительные метаданные
```

### 4. **ExampleLibrary** - Библиотека Примеров

Управляет хранением и извлечением примеров:

```python
class ExampleLibrary:
    async def get_examples(
        section_type: str,
        limit: int = 3,
        min_quality: float = 0.7,
        tags: List[str] = None
    ) -> List[FewShotExample]

    async def add_example(example: FewShotExample) -> str

    async def remove_example(example_id: str) -> bool

    async def get_example_stats() -> Dict[str, Any]
```

**Возможности:**

- Фильтрация по типу секции, качеству, тегам
- Автоматический выбор лучших примеров
- Отслеживание статистики использования
- Индексация для быстрого поиска

### 5. **SectionPatternLibrary** - Библиотека Паттернов

Хранит и предоставляет структурные паттерны:

```python
class SectionPatternLibrary:
    async def get_patterns(
        section_type: str,
        pattern_types: List[str] = None
    ) -> List[SectionPattern]

    async def add_pattern(pattern: SectionPattern) -> str
```

## Использование

### Базовая Генерация Секции

```python
from core.groupagents.writer_agent import WriterAgent

# Инициализация
writer = WriterAgent()

# Данные клиента
client_data = {
    "beneficiary_name": "Dr. Elena Rodriguez",
    "field": "Computational Biology",
    "evidence": [
        {
            "title": "NIH Director's Pioneer Award",
            "description": "Prestigious award for groundbreaking research..."
        },
        {
            "title": "Best Paper Award at ISMB",
            "description": "Selected from 800+ submissions..."
        }
    ]
}

# Генерация секции
section = await writer.agenerate_legal_section(
    section_type="awards",
    client_data=client_data,
    use_patterns=True,
    user_id="user_123"
)

# Доступ к результату
print(f"Title: {section.title}")
print(f"Content:\n{section.content}")
print(f"Confidence: {section.confidence_score:.2f}")
print(f"Suggestions: {section.suggestions}")
```

### Добавление Пользовательского Примера

```python
# Создание высококачественного примера
custom_example = {
    "section_type": "contributions",
    "criterion_name": "Original Contributions of Major Significance",
    "input_data": {
        "beneficiary": "Dr. Sarah Johnson",
        "field": "Renewable Energy",
        "contributions": [...]
    },
    "generated_content": """
        **Original Contributions of Major Significance**

        Dr. Johnson has made groundbreaking contributions...
        [Полный текст примера]
    """,
    "quality_score": 0.95,
    "tags": ["contributions", "renewable_energy", "high_quality"]
}

# Добавление в библиотеку
example_id = await writer.aadd_example(custom_example, user_id="user_123")

# Использование в генерации
section = await writer.agenerate_legal_section(
    section_type="contributions",
    client_data=new_client_data,
    examples=[example_id],  # Явное указание примеров
    user_id="user_123"
)
```

### Генерация Нескольких Типов Секций

```python
section_types = ["awards", "press", "judging", "membership", "contributions"]

sections = {}
for section_type in section_types:
    section = await writer.agenerate_legal_section(
        section_type=section_type,
        client_data=client_data,
        user_id="user_123"
    )
    sections[section_type] = section
    print(f"{section_type}: {section.confidence_score:.2f}")
```

### Получение Статистики

```python
stats = await writer.get_stats()

print(f"Total Sections: {stats['total_sections_generated']}")
print(f"Example Library:")
print(f"  - Total Examples: {stats['example_library_stats']['total_examples']}")
print(f"  - Average Quality: {stats['example_library_stats']['average_quality']:.2f}")
print(f"  - Examples by Type: {stats['example_library_stats']['examples_by_type']}")
```

## Архитектура Генерации

### Процесс Few-Shot Learning

1. **Выбор Примеров**
   - Автоматический выбор 3 лучших примеров для типа секции
   - Фильтрация по качеству (min_quality >= 0.75)
   - Сортировка по quality_score и usage_count

2. **Извлечение Паттернов**
   - Получение структурных паттернов для типа секции
   - 4 типа: opening, evidence_analysis, conclusion, comparative_analysis
   - Каждый паттерн содержит шаблоны и юридические фразы

3. **Построение Контекста**
   - Объединение примеров, паттернов и данных клиента
   - Форматирование для промпта LLM
   - Добавление инструкций для типа секции

4. **Генерация Контента**
   - Использование примеров для обучения стиля
   - Применение паттернов для структуры
   - Адаптация к данным конкретного клиента

5. **Оценка Качества**
   - Расчёт confidence_score на основе:
     - Использования примеров (+0.2)
     - Применения паттернов (+0.15)
     - Длины контента (+0.1)
     - Юридических фраз (+0.15)

6. **Генерация Рекомендаций**
   - Предложения по улучшению контента
   - Проверка на наличие ключевых элементов
   - Рекомендации по длине и структуре

## Типы Секций

### Awards (8 CFR § 204.5(h)(3)(i))

**Фокус:**
- Престиж и признание наград
- Конкурентный отбор
- Национальное/международное значение

**Примеры:**
- Best Paper Awards
- Research Grants (NIH, NSF)
- Professional Society Awards

### Press (8 CFR § 204.5(h)(3)(iii))

**Фокус:**
- Крупные публикации
- Независимое авторство
- Фокус на достижениях бенефициара

**Примеры:**
- Scientific American
- Nature News
- Major newspapers

### Judging (8 CFR § 204.5(h)(3)(iv))

**Фокус:**
- Признание экспертизы
- Роль оценщика
- Peer review обязанности

**Примеры:**
- Conference Program Committee
- Journal Reviewer
- Grant Panel Member

### Membership (8 CFR § 204.5(h)(3)(ii))

**Фокус:**
- Избирательное членство
- Выдающиеся требования
- Профессиональный статус

**Примеры:**
- National Academy of Sciences
- IEEE Fellow
- Exclusive professional societies

### Contributions (8 CFR § 204.5(h)(3)(v))

**Фокус:**
- Оригинальность вклада
- Значительность для области
- Влияние и признание

**Примеры:**
- Novel algorithms
- Breakthrough research
- Industry standards

## Структурные Паттерны

### Opening Pattern

```
{beneficiary} has {achievement_summary} in {field}. This {evidence_type}
demonstrates {quality_descriptor} and satisfies the regulatory requirements
of 8 CFR § {regulation_code}.
```

**Используется в:** awards, press, judging, membership, contributions

### Evidence Analysis Pattern

```
**{evidence_title}** ({date})

**{descriptor_1}:** {value_1}
**{descriptor_2}:** {value_2}

**Significance:** {significance_explanation}

**Evidence:** {exhibit_reference}
```

**Используется в:** awards, press, judging, contributions

### Conclusion Pattern

```
**Conclusion**

The {evidence_summary} clearly establishes {possessive} {quality_statement}
in {field}. {supporting_statement}

Per *{case_citation}*, {legal_standard}. The {evidence_characteristics}
meet these standards and demonstrate extraordinary ability.
```

**Используется в:** Все типы секций

### Comparative Analysis Pattern

```
**Comparative Analysis**

{possessive} {count} {evidence_type} place {last_name} among the top echelon
of professionals in {field}. Industry data indicates that fewer than {percentage}%
of practitioners in {field} achieve {achievement_descriptor}.
```

**Используется в:** awards, press, contributions

## Юридические Ссылки

### Основные Случаи

- **Kazarian v. USCIS, 596 F.3d 1115 (9th Cir. 2010)**
  - Двухступенчатый анализ EB-1A
  - Plain language interpretation

- **Visinscaia v. Beers, 4 F. Supp. 3d 126 (D.D.C. 2013)**
  - Membership и Original Contributions

- **Grimson v. INS, No. 96-1426 (4th Cir. 1997)**
  - Press coverage standards

- **Buletini v. INS, 860 F. Supp. 1222 (E.D. Mich. 1994)**
  - Awards evaluation

### Регуляторные Коды

- **8 CFR § 204.5(h)(3)(i)** - Awards
- **8 CFR § 204.5(h)(3)(ii)** - Membership
- **8 CFR § 204.5(h)(3)(iii)** - Press
- **8 CFR § 204.5(h)(3)(iv)** - Judging
- **8 CFR § 204.5(h)(3)(v)** - Original Contributions
- **8 CFR § 204.5(h)(3)(vi)** - Scholarly Articles
- **8 CFR § 204.5(h)(3)(vii)** - Exhibitions
- **8 CFR § 204.5(h)(3)(viii)** - Leading Role
- **8 CFR § 204.5(h)(3)(ix)** - High Salary
- **8 CFR § 204.5(h)(3)(x)** - Commercial Success

## Оценка Качества

### Confidence Score Calculation

```python
base_score = 0.5

# Examples bonus: +0.2 max (0.07 per example)
if examples_used:
    score += min(0.2, len(examples) * 0.07)

# Patterns bonus: +0.15 max (0.05 per pattern)
if patterns_used:
    score += min(0.15, len(patterns) * 0.05)

# Content length bonus: +0.1
if 300 <= word_count <= 800:
    score += 0.1
elif 200 <= word_count <= 1000:
    score += 0.05

# Legal phrases bonus: +0.15 max (0.04 per phrase)
legal_phrases = ["8 CFR", "Kazarian", "regulatory requirements", "extraordinary ability"]
score += min(0.15, found_count * 0.04)

final_score = min(1.0, score)
```

### Suggestions Generation

Система автоматически генерирует предложения по улучшению:

1. **Длина контента**
   - < 200 слов: "Consider expanding..."
   - > 900 слов: "Consider condensing..."

2. **Количество доказательств**
   - < 3 items: "Add more evidence..."

3. **Юридические элементы**
   - Отсутствие "8 CFR": "Include regulatory citation..."
   - Отсутствие "Kazarian": "Consider citing Kazarian..."

4. **Язык**
   - Отсутствие "extraordinary/exceptional": "Strengthen language..."

## Интеграция с LLM

### Промпт-инжиниринг

Система строит структурированный промпт:

```
Generate a {section_type} section for an EB-1A petition.

Beneficiary: {name}
Field: {field}
Evidence Count: {count}

Instructions:
{section_specific_instructions}

=== EXAMPLES OF HIGH-QUALITY SECTIONS ===

Example 1 (Quality: 0.90):
Input: {...}
Output: {...}

Example 2 (Quality: 0.85):
Input: {...}
Output: {...}

=== STRUCTURAL PATTERNS TO FOLLOW ===

OPENING Pattern:
Structure: {template}
Example Phrases: {...}
Legal Language: {...}

=== CLIENT DATA ===

Evidence Items: 3
1. {evidence_1}
2. {evidence_2}
3. {evidence_3}

Now generate a high-quality section following the examples and patterns above:
```

### Будущая Интеграция

В текущей реализации используется `_simulate_llm_generation()` для демонстрации.
Для продакшн-использования необходимо заменить на вызов реального LLM API:

```python
async def _generate_with_patterns(self, context, section_type, client_data):
    prompt = self._build_generation_prompt(context)

    # Вызов LLM (OpenAI, Anthropic, etc.)
    response = await self.llm_client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "You are an expert EB-1A petition writer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1500
    )

    content = response.choices[0].message.content

    # Далее обработка как обычно...
```

## Расширение Системы

### Добавление Новых Типов Секций

1. Добавить тип в `_get_section_instructions()`:

```python
def _get_section_instructions(self, section_type: str) -> str:
    instructions = {
        # ... существующие ...
        "new_section_type": "Instructions for new section type..."
    }
    return instructions.get(section_type, "...")
```

2. Добавить заголовок в `_get_section_title()`:

```python
def _get_section_title(self, section_type: str) -> str:
    titles = {
        # ... существующие ...
        "new_section_type": "New Section Title"
    }
    return titles.get(section_type, "...")
```

3. Создать примеры и паттерны для нового типа

### Улучшение Примеров

Добавляйте реальные успешные примеры в библиотеку:

```python
# После успешной генерации и одобрения
if section.confidence_score >= 0.9 and user_approved:
    example = FewShotExample(
        section_type=section.section_type,
        criterion_name=section.title,
        input_data=original_client_data,
        generated_content=section.content,
        quality_score=0.95,
        tags=["approved", "high_quality", custom_tags...],
    )
    await writer._example_library.add_example(example)
```

### Настройка Паттернов

Создавайте специализированные паттерны для конкретных индустрий:

```python
tech_opening_pattern = SectionPattern(
    pattern_type="opening",
    section_types=["awards", "contributions"],
    template_structure="{beneficiary}, a pioneering {role} in {tech_field}, has {achievement}...",
    example_phrases=[
        "has revolutionized the field of {field}",
        "has developed groundbreaking technology in {area}",
    ],
    legal_language_hints=[...],
    variables=["beneficiary", "role", "tech_field", "achievement"],
    metadata={"industry": "technology", "specialization": "software"}
)

await writer._section_patterns.add_pattern(tech_opening_pattern)
```

## Преимущества Системы

### 1. Консистентность

- Единый стиль и качество всех секций
- Соблюдение юридических стандартов
- Переиспользование проверенных формулировок

### 2. Обучаемость

- Система улучшается с каждым новым примером
- Автоматическое ранжирование примеров по quality_score
- Отслеживание наиболее эффективных паттернов

### 3. Адаптивность

- Легко добавлять новые типы секций
- Настраиваемые паттерны для разных индустрий
- Гибкая фильтрация примеров по тегам

### 4. Прозрачность

- Отслеживание использованных примеров и паттернов
- Confidence score для оценки качества
- Конкретные рекомендации по улучшению

### 5. Масштабируемость

- Библиотека примеров растёт автоматически
- Индексация для быстрого поиска
- Эффективная работа с большим количеством примеров

## Лучшие Практики

### 1. Качество Примеров

- Используйте только одобренные, успешные примеры
- Поддерживайте quality_score >= 0.8
- Регулярно обновляйте примеры новыми успешными кейсами

### 2. Тегирование

- Используйте детальные теги: индустрия, специализация, тип доказательств
- Теги помогают в точной фильтрации примеров
- Примеры: ["tech", "ai", "awards", "peer_reviewed", "international"]

### 3. Паттерны

- Создавайте специализированные паттерны для разных индустрий
- Обновляйте юридические ссылки при изменении законодательства
- Тестируйте новые паттерны на контрольной выборке

### 4. Оценка Качества

- Всегда проверяйте confidence_score
- Следуйте рекомендациям из suggestions
- Человеческий review обязателен для финальной версии

### 5. Аудит

- Все генерации логируются через memory.alog_audit()
- Отслеживайте метрики: confidence_score, word_count, usage_count
- Анализируйте наиболее эффективные примеры и паттерны

## Известные Ограничения

1. **LLM Симуляция**
   - Текущая версия использует заглушку `_simulate_llm_generation()`
   - Для продакшн требуется интеграция с реальным LLM API

2. **Качество Контента**
   - Автоматически сгенерированный контент требует review
   - Юридическая экспертиза обязательна перед подачей

3. **Специфичность Индустрии**
   - Базовые примеры достаточно общие
   - Рекомендуется добавлять индустрии-специфичные примеры

4. **Языковая Поддержка**
   - Текущая версия оптимизирована для английского
   - Для других языков требуется адаптация примеров и паттернов

## Дорожная Карта

### Ближайшие Улучшения

1. **Интеграция с LLM**
   - Подключение OpenAI GPT-5
   - Anthropic Claude
   - Azure OpenAI

2. **Расширенная Аналитика**
   - Dashboard для мониторинга качества
   - A/B тестирование паттернов
   - Анализ наиболее эффективных примеров

3. **Персонализация**
   - Индустрии-специфичные библиотеки
   - Настраиваемые стили письма
   - Адаптация к предпочтениям юриста

4. **Автоматизация**
   - Автоматическое добавление успешных примеров
   - ML-based quality scoring
   - Автоматическая оптимизация паттернов

### Долгосрочные Цели

- Мультиязыковая поддержка
- Интеграция с case management системами
- Экспорт в различные форматы (PDF, DOCX)
- Collaborative editing с версионированием

## Контакты и Поддержка

Для вопросов и предложений по улучшению:

- Documentation: См. код в `core/groupagents/writer_agent.py`
- Examples: См. `test_writer_agent_few_shot.py`
- Issues: Создавайте issue в репозитории проекта

---

**Версия:** 1.0.0
**Дата:** 2025-01-16
**Статус:** Production Ready (требуется LLM интеграция)
