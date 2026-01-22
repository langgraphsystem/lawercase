# 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: Данные анкеты не сохраняются в базу

**Дата**: 2025-11-28
**Case ID**: 6139bc5d-351c-4696-a80f-0dd34d15654e
**User ID**: 7314014306
**Статус**: ❌ КРИТИЧЕСКИЙ БАГ ОБНАРУЖЕН

---

## 📊 Фактическое состояние

### ✅ Что работает:
1. **Кейс создан успешно**
   - Case ID: 6139bc5d-351c-4696-a80f-0dd34d15654e
   - Title: "E2 NIW Frank Gourd"
   - Status: draft
   - Created: 2025-11-28 00:53:33

2. **Intake Progress работает**
   - Current Block: family_childhood (второй блок!)
   - Completed Blocks: ['basic_info'] (первый блок завершен!)
   - Всего блоков: 11
   - Updated: 2025-11-28 01:05:37

3. **Логи показывают события "сохранено"**
   - 6 событий `intake.response_saved_to_memory`
   - Ответы: full_name, date_of_birth, place_of_birth, citizenship, current_residence, main_field

### ❌ Что НЕ работает:
**SEMANTIC MEMORY: 0 ЗАПИСЕЙ В БАЗЕ ДАННЫХ!**

Проверка базы данных показывает:
```sql
SELECT COUNT(*) FROM mega_agent.semantic_memory
WHERE user_id = '7314014306';
-- Результат: 0
```

---

## 🔍 Корневая причина

### Проблема №1: MemoryManager создается без embedder

**Файл**: `telegram_interface/bot.py:50`

```python
# ТЕКУЩИЙ КОД (НЕПРАВИЛЬНО):
memory_manager = MemoryManager(semantic=SupabaseSemanticStore())
#                                       ❌ НЕТ embedder параметра!
```

**Что происходит**:
1. `MemoryManager.__init__()` устанавливает `self.embedder = _NoOpEmbedder()` (дефолт)
2. `SupabaseSemanticStore.__init__()` создает СВОЙ embedder
3. `MemoryManager.awrite()` пытается создать embeddings через NoOpEmbedder
4. `SupabaseSemanticStore.ainsert()` также пытается создать embeddings

**Результат**: Двойная попытка создания embeddings или полный провал

### Проблема №2: Нет HTTP запросов к OpenAI API

Логи показывают:
- ✅ HTTP запросы к Telegram API (sendMessage)
- ✅ Запросы к базе данных (Case retrieved)
- ❌ **НЕТ запросов к OpenAI API для создания embeddings!**

Это означает, что embeddings НЕ создаются вообще.

### Проблема №3: Transaction commit происходит, но данные не сохраняются

`DatabaseManager.session()` context manager (connection.py:120):
```python
async with factory() as session:
    try:
        yield session
        await session.commit()  # ← Commit вызывается
    except Exception:
        await session.rollback()
        raise
```

НО: В логах нет exceptions, commit происходит, данные не сохраняются!

---

## 💡 Гипотеза

**SupabaseSemanticStore.ainsert()** падает молча при попытке создать embeddings:

1. Метод вызывается: `await self.embedder.aembed_documents(texts)` (line 48)
2. Embedder требует OpenAI API key
3. Если API key невалидный или expired → silent failure
4. Записи НЕ добавляются в session через `session.add()`
5. Context manager делает commit ПУСТОЙ транзакции
6. Логи показывают "saved_to_memory" (потому что exception не выбрасывается в intake_handlers.py)

---

## 🔧 Исправление

### Вариант 1: Упростить - использовать MemoryManager без embeddings (БЫСТРО)

**Файл**: `telegram_interface/bot.py`

```python
# ИСПРАВЛЕНИЕ:
from core.memory.stores.semantic_store import SemanticStore  # in-memory для тестирования

# Временное решение - использовать in-memory store для проверки логики
memory_manager = MemoryManager(semantic=SemanticStore())
mega_agent = mega_agent or MegaAgent(memory_manager=memory_manager)
```

**Плюсы**: Быстро проверить, что логика сохранения работает
**Минусы**: Данные в памяти, теряются при перезапуске

### Вариант 2: Исправить SupabaseSemanticStore (ПРАВИЛЬНО)

#### Шаг 1: Добавить детальное логирование в SupabaseSemanticStore

**Файл**: `core/memory/stores/supabase_semantic_store.py`

```python
async def ainsert(self, records: Iterable[MemoryRecord]) -> int:
    """Insert memory records with Supabase embeddings."""
    records_list = list(records)
    if not records_list:
        return 0

    logger.info(f"supabase_semantic_store.ainsert.start", count=len(records_list))

    texts = [record.text for record in records_list]

    try:
        logger.info(f"supabase_semantic_store.creating_embeddings", texts_count=len(texts))
        embeddings = await self.embedder.aembed_documents(texts)
        logger.info(f"supabase_semantic_store.embeddings_created", embeddings_count=len(embeddings))
    except Exception as e:
        logger.error(f"supabase_semantic_store.embedding_failed", error=str(e), exc_info=True)
        raise  # RE-RAISE для видимости!

    if len(embeddings) != len(records_list):
        raise ValueError("Mismatch between records and embeddings count")

    async with self.db.session() as session:
        for record, embedding in zip(records_list, embeddings, strict=False):
            record_id = _ensure_uuid(record.id)
            record.id = str(record_id)

            # Collect metadata including case_id
            metadata = {
                "thread_id": record.thread_id,
                "case_id": record.case_id,
                "salience": record.salience,
                "confidence": record.confidence,
                "tags": record.tags,
            }

            if record.metadata:
                metadata.update(record.metadata)

            db_record = SemanticMemoryDB(
                record_id=record_id,
                namespace=self.namespace,
                user_id=record.user_id or "anonymous",
                thread_id=record.thread_id,
                text=record.text,
                type=record.type,
                source=record.source,
                tags=record.tags,
                metadata_json={k: v for k, v in metadata.items() if v is not None},
                embedding=embedding,
                embedding_model=self.embedding_model,
                embedding_dimension=self.embedding_dimension,
            )
            session.add(db_record)
            logger.debug(f"supabase_semantic_store.record_added", record_id=record_id, user_id=record.user_id)

    logger.info(f"supabase_semantic_store.ainsert.complete", count=len(records_list))
    return len(records_list)
```

#### Шаг 2: Проверить переменные окружения в Railway

```bash
railway variables | grep -E "(OPENAI_API_KEY|SUPABASE_VECTOR_URL)"
```

Убедиться, что:
- ✅ OPENAI_API_KEY установлен и валиден
- ✅ SUPABASE_VECTOR_URL установлен (уже добавили!)

#### Шаг 3: Перезапустить Railway и проверить логи

```bash
railway logs --tail 100
```

Ожидаемый вывод:
```
[INFO] supabase_semantic_store.ainsert.start count=1
[INFO] supabase_semantic_store.creating_embeddings texts_count=1
[INFO] HTTP Request: POST https://api.openai.com/v1/embeddings ...
[INFO] supabase_semantic_store.embeddings_created embeddings_count=1
[INFO] supabase_semantic_store.record_added record_id=... user_id=7314014306
[INFO] supabase_semantic_store.ainsert.complete count=1
```

### Вариант 3: Использовать существующий Supabase Embedder (ОПТИМАЛЬНО)

**Файл**: `telegram_interface/bot.py`

```python
from core.memory.stores.supabase_semantic_store import SupabaseSemanticStore
from core.llm.supabase_embedder import create_supabase_embedder

# Create shared embedder
embedder = create_supabase_embedder()

# Use same embedder for both MemoryManager and SupabaseSemanticStore
semantic_store = SupabaseSemanticStore(embedder=embedder)
memory_manager = MemoryManager(semantic=semantic_store, embedder=embedder)
mega_agent = mega_agent or MegaAgent(memory_manager=memory_manager)
```

**Плюсы**:
- Единый embedder, нет дублирования
- Правильная архитектура
- Кеширование embeddings

---

## 🧪 Проверка после исправления

### 1. Проверить логи на наличие embedding запросов:

```bash
railway logs --tail 200 | grep -E "(openai|embedding|supabase_semantic_store)"
```

### 2. Проверить базу данных:

```sql
SELECT COUNT(*) as count, user_id
FROM mega_agent.semantic_memory
WHERE user_id = '7314014306'
GROUP BY user_id;
```

Ожидаемый результат: count > 0

### 3. Проверить сохраненные ответы:

```sql
SELECT text, metadata_json->>'question_id' as question_id, created_at
FROM mega_agent.semantic_memory
WHERE metadata_json->>'case_id' = '6139bc5d-351c-4696-a80f-0dd34d15654e'
ORDER BY created_at ASC;
```

Ожидаемый результат: 6 записей (или больше, если анкета продолжается)

---

## 📝 Итоговый отчет

### Проблема:
1. ✅ Логи показывают "intake.response_saved_to_memory"
2. ❌ База данных показывает 0 записей в semantic_memory
3. ❌ Нет HTTP запросов к OpenAI API для embeddings

### Причина:
- MemoryManager создается без правильного embedder
- SupabaseSemanticStore не может создать embeddings
- Silent failure при создании embeddings
- Commit происходит на пустой транзакции

### Решение:
1. Добавить детальное логирование в SupabaseSemanticStore.ainsert()
2. Проверить OPENAI_API_KEY в Railway
3. Использовать shared embedder для MemoryManager и SupabaseSemanticStore
4. Перезапустить Railway
5. Проверить логи и базу данных

### Статус:
🔴 **КРИТИЧЕСКИЙ БАГ** - требует немедленного исправления
🎯 **Приоритет**: ВЫСОКИЙ - данные пользователей теряются

---

**Дата отчета**: 2025-11-28 01:12 UTC
**Следующие шаги**: Применить Вариант 3 (оптимальное решение) и проверить
