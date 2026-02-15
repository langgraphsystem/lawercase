# EB-1A Knowledge Base - Использование агентами

## Обзор

База знаний EB-1A содержит официальную информацию USCIS:
- **571 чанков** из 23 документов
- Формы: I-140, I-907, I-485, G-1055 и др.
- Политики: Policy Manual Vol.6, Kazarian case
- Гайды: Filing addresses, fees, premium processing

## Быстрый старт

```python
from core.knowledge.eb1a_knowledge_base import EB1AKnowledgeBase, search_eb1a_knowledge

# Быстрый поиск (одна строка)
results = await search_eb1a_knowledge("extraordinary ability criteria")

# Полный доступ через класс
kb = EB1AKnowledgeBase()
```

## Примеры использования

### 1. Поиск по ключевым словам

```python
kb = EB1AKnowledgeBase()

# Поиск информации о критериях
results = await kb.search("8 CFR 204.5", limit=10)

# Поиск о премиум-обработке
results = await kb.search("premium processing time", limit=5)

# Поиск по типу документа
forms = await kb.search("I-140", document_type="forms")
```

### 2. Получение информации о критериях EB-1A

```python
# Информация о всех 10 критериях
all_criteria = await kb.get_criteria_info()

# Информация о конкретном критерии (1-10)
criterion_5 = await kb.get_criteria_info(5)  # Original Contributions
criterion_8 = await kb.get_criteria_info(8)  # Leading/Critical Role
```

Номера критериев:
| # | Название | Описание |
|---|----------|----------|
| 1 | Awards | Призы и награды |
| 2 | Membership | Членство в ассоциациях |
| 3 | Published Material | Публикации о заявителе |
| 4 | Judging | Судейство работ других |
| 5 | Original Contributions | Оригинальные вклады |
| 6 | Scholarly Articles | Научные статьи |
| 7 | Exhibitions | Художественные выставки |
| 8 | Leading Role | Ведущая/критическая роль |
| 9 | High Salary | Высокая зарплата |
| 10 | Commercial Success | Коммерческий успех |

### 3. Информация о формах USCIS

```python
# Информация о форме I-140
i140_info = await kb.get_form_info("I-140")

# Информация о премиум-обработке (I-907)
i907_info = await kb.get_form_info("I-907")
```

### 4. Kazarian Two-Step Analysis

```python
# Получить информацию о Kazarian v. USCIS
kazarian = await kb.get_kazarian_analysis()

# Или прямой поиск
kazarian = await kb.search("Kazarian two-step", limit=10)
```

### 5. Информация о сборах

```python
fees = await kb.get_fees_info()
```

### 6. Получение полного документа

```python
# Получить все чанки документа по ID
chunks = await kb.get_document("form-i140")
full_text = " ".join(c['content'] for c in chunks)

# ID документов:
# - form-i140, form-i907, form-g1055, form-g1450, etc.
# - policy-vol6-partE, policy-vol6-partF-ch1, policy-vol6-partF-ch2
# - caselaw-kazarian
# - guide-eb1-main, guide-evidence-checklist, etc.
```

### 7. Статистика базы знаний

```python
stats = await kb.get_stats()
print(f"Всего чанков: {stats['total_chunks']}")
print(f"Уникальных документов: {stats['unique_documents']}")
print(f"По типам: {stats['by_type']}")
```

## Интеграция с агентами

### В MegaAgent

```python
from core.knowledge.eb1a_knowledge_base import EB1AKnowledgeBase

class EB1AAgent:
    def __init__(self):
        self.kb = EB1AKnowledgeBase()

    async def answer_question(self, question: str) -> str:
        # Поиск релевантной информации
        context = await self.kb.search(question, limit=5)

        # Формирование контекста для LLM
        context_text = "\n\n".join([
            f"[{c['document_name']}]: {c['content']}"
            for c in context
        ])

        # Передача в LLM
        return await self.llm.generate(
            f"Context:\n{context_text}\n\nQuestion: {question}"
        )
```

### В RAG Pipeline

```python
from core.knowledge.eb1a_knowledge_base import EB1AKnowledgeBase

async def enrich_with_eb1a_knowledge(query: str) -> str:
    kb = EB1AKnowledgeBase()
    results = await kb.search(query, limit=3)

    if not results:
        return ""

    return "\n".join([
        f"Source: {r['document_name']}\n{r['content']}"
        for r in results
    ])
```

## Доступные документы

### Формы (forms/)
- Form I-140 - Immigrant Petition
- Form I-907 - Premium Processing
- Form I-485 - Adjustment of Status
- Form G-1055 - Fee Schedule
- Form G-1450 - Credit Card Authorization
- Form G-1650 - ACH Authorization
- Form G-1145 - E-Notification
- Form G-28 - Attorney Notice
- Form I-131 - Travel Document
- Form I-765 - EAD

### Политики (policy/)
- Policy Manual Vol.6 Part E - Employment-Based Overview
- Policy Manual Vol.6 Part F Ch.1 - EB-1 Background
- Policy Manual Vol.6 Part F Ch.2 - EB-1A Criteria
- Kazarian v. USCIS (9th Cir. 2010) - Landmark case

### Гайды (guides/)
- EB-1 Main Page
- I-140 Evidence Checklist
- I-140 Filing Addresses
- Premium Processing Guide
- Fee Schedule

## Прямой SQL-запрос

Если нужен прямой доступ к Supabase:

```python
from supabase import create_client
import os

client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Поиск
result = client.table("knowledge_base")\
    .select("content, metadata")\
    .eq("namespace", "eb1a")\
    .ilike("content", "%extraordinary%")\
    .limit(10)\
    .execute()
```
