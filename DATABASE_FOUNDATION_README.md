# 🗄️ Database Foundation - Phase 1 Implementation

## ✅ Что реализовано

Полная замена in-memory хранилищ на production-ready инфраструктуру:

### 1. **PostgreSQL** - Metadata & Audit
- ✅ Semantic memory metadata (векторы хранятся в Pinecone)
- ✅ Episodic memory (audit trail)
- ✅ RMT buffers (working memory)
- ✅ Cases & Documents metadata
- ✅ Async connection pooling
- ✅ SQLAlchemy models with proper indexes

### 2. **Pinecone** - Vector Search
- ✅ Serverless vector index (2048-dim)
- ✅ Cosine similarity search
- ✅ Metadata filtering for multi-tenancy
- ✅ Automatic index creation

### 3. **Voyage AI** - Embeddings
- ✅ voyage-3-large model (2048 dimensions)
- ✅ Optimized for document vs query
- ✅ Automatic text truncation

### 4. **Cloudflare R2** - Document Storage
- ✅ S3-compatible API
- ✅ PDF, images, scans storage
- ✅ Presigned URLs generation
- ✅ Metadata storage

---

## 📂 Структура файлов

```
core/
├── storage/
│   ├── __init__.py              # Public API exports
│   ├── config.py                # Unified configuration
│   ├── connection.py            # PostgreSQL connection manager
│   ├── models.py                # SQLAlchemy models
│   ├── pinecone_store.py        # Pinecone vector store
│   ├── r2_storage.py            # Cloudflare R2 client
│   ├── postgres_stores.py       # PostgresEpisodicStore & PostgresWorkingMemory
│   └── migrations/              # Alembic migrations
├── llm/
│   └── voyage_embedder.py       # Voyage AI embeddings client
└── memory/
    ├── memory_manager.py        # Updated to use new stores
    └── stores/
        ├── semantic_store.py    # Now uses Pinecone
        ├── episodic_store.py    # Now uses PostgreSQL
        └── working_memory.py    # Now uses PostgreSQL

requirements_storage.txt         # New dependencies
.env.example                     # Configuration template
```

---

## 🚀 Быстрый старт

### 1. Установить зависимости

```bash
# Установить новые зависимости
pip install -r requirements_storage.txt

# Или установить отдельно:
pip install sqlalchemy[asyncio] asyncpg alembic
pip install pinecone-client voyageai boto3
pip install pydantic-settings
```

### 2. Настроить окружение

Скопировать `.env.example` в `.env` и заполнить:

```bash
cp .env.example .env
nano .env  # или используйте ваш любимый редактор
```

**Обязательные переменные:**

```env
# PostgreSQL
POSTGRES_DSN=postgresql+asyncpg://user:password@localhost:5432/megaagent  # pragma: allowlist secret

# Pinecone
PINECONE_API_KEY=pc-xxxxx
PINECONE_INDEX_NAME=mega-agent-semantic

# Voyage AI
VOYAGE_API_KEY=pa-xxxxx

# Cloudflare R2
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_BUCKET_NAME=mega-agent-documents
```

### 3. Создать PostgreSQL database

```bash
# Вариант 1: Локальный PostgreSQL
createdb megaagent

# Вариант 2: Docker
docker run -d \
  --name megaagent-postgres \
  -e POSTGRES_DB=megaagent \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:16-alpine

# Вариант 3: Cloud (Railway, Supabase, AWS RDS)
# Используйте connection string из панели управления
```

### 4. Инициализировать database schema

```python
# create_schema.py
import asyncio
from core.storage.connection import get_db_manager

async def init_db():
    db = get_db_manager()

    # Create schema
    await db.create_schema()

    # Create all tables
    await db.create_all_tables()

    print("✅ Database initialized!")

if __name__ == "__main__":
    asyncio.run(init_db())
```

```bash
python create_schema.py
```

### 5. Проверить подключение

```python
# test_storage.py
import asyncio
from core.storage.connection import get_db_manager
from core.storage.pinecone_store import create_pinecone_store
from core.storage.r2_storage import create_r2_storage
from core.llm.voyage_embedder import create_voyage_embedder

async def test_connections():
    # Test PostgreSQL
    db = get_db_manager()
    pg_ok = await db.health_check()
    print(f"PostgreSQL: {'✅' if pg_ok else '❌'}")

    # Test Pinecone
    pinecone = create_pinecone_store()
    pc_ok = await pinecone.health_check()
    print(f"Pinecone: {'✅' if pc_ok else '❌'}")

    # Test R2
    r2 = create_r2_storage()
    r2_ok = await r2.health_check()
    print(f"R2: {'✅' if r2_ok else '❌'}")

    # Test Voyage embeddings
    voyage = create_voyage_embedder()
    embedding = await voyage.aembed_query("test")
    print(f"Voyage: ✅ (dimension: {len(embedding)})")

if __name__ == "__main__":
    asyncio.run(test_connections())
```

---

## 📖 Использование

### Semantic Memory с Pinecone

```python
from core.storage.pinecone_store import create_pinecone_store
from core.llm.voyage_embedder import create_voyage_embedder
from core.memory.models import MemoryRecord

# Initialize
pinecone = create_pinecone_store()
voyage = create_voyage_embedder()

# Create memory record
record = MemoryRecord(
    user_id="user_123",
    text="Important legal precedent from case XYZ",
    type="fact",
    source="case_analysis",
    tags=["legal", "precedent"]
)

# Generate embedding
embedding = await voyage.aembed_documents([record.text])

# Store in Pinecone
await pinecone.upsert([record], embedding)

# Search similar memories
query_embedding = await voyage.aembed_query("find legal precedents")
results = await pinecone.search(
    query_embedding,
    user_id="user_123",
    topk=5
)

for result in results:
    print(f"Score: {result['score']}")
    print(f"Text: {result['metadata']['text']}")
```

### Episodic Memory (Audit Trail)

```python
from core.storage.postgres_stores import PostgresEpisodicStore
from core.memory.models import AuditEvent
from uuid import uuid4

store = PostgresEpisodicStore()

# Log audit event
event = AuditEvent(
    event_id=str(uuid4()),
    user_id="user_123",
    thread_id="case_456",
    source="case_agent",
    action="create_case",
    payload={"case_id": "case_456", "title": "New Case"}
)

await store.aappend(event)

# Retrieve thread history
events = await store.aget_thread_events("case_456")
for event in events:
    print(f"{event.timestamp}: {event.action}")
```

### Document Storage в R2

```python
from core.storage.r2_storage import create_r2_storage

r2 = create_r2_storage()

# Upload document
with open("case_document.pdf", "rb") as f:
    result = await r2.upload_file(
        file_content=f,
        filename="case_document.pdf",
        content_type="application/pdf",
        folder="cases/123",
        metadata={"case_id": "123", "document_type": "evidence"}
    )

print(f"Uploaded: {result['r2_key']}")
print(f"URL: {result['r2_url']}")

# Generate presigned URL (1 hour expiration)
presigned_url = await r2.generate_presigned_url(
    result['r2_key'],
    expiration=3600,
    force_download=True
)

# Download document
content = await r2.download_file(result['r2_key'])
```

---

## 🔧 Миграции (Alembic)

### Setup Alembic

```bash
# Initialize Alembic
alembic init core/storage/migrations

# Edit alembic.ini to use env variable
# sqlalchemy.url = driver://user:pass@localhost/dbname  # pragma: allowlist secret
```

### Создать миграцию

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Add new column to cases table"

# Run migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 🧪 Тестирование

```python
# tests/test_storage.py
import pytest
from core.storage.pinecone_store import create_pinecone_store
from core.llm.voyage_embedder import create_voyage_embedder

@pytest.mark.asyncio
async def test_pinecone_upsert_and_search():
    pinecone = create_pinecone_store(namespace="test")
    voyage = create_voyage_embedder()

    # Create test record
    record = MemoryRecord(
        user_id="test_user",
        text="test memory",
        type="fact"
    )

    # Generate embedding and upsert
    embedding = await voyage.aembed_documents([record.text])
    count = await pinecone.upsert([record], embedding)

    assert count == 1

    # Search
    query_emb = await voyage.aembed_query("test")
    results = await pinecone.search(query_emb, user_id="test_user")

    assert len(results) > 0
    assert results[0]['metadata']['text'] == "test memory"

    # Cleanup
    await pinecone.delete_all()
```

---

## 📊 Мониторинг

### PostgreSQL

```sql
-- Check connection pool
SELECT * FROM pg_stat_activity WHERE datname = 'megaagent';

-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'mega_agent'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Slow queries
SELECT * FROM pg_stat_statements
WHERE query LIKE '%mega_agent%'
ORDER BY mean_exec_time DESC LIMIT 10;
```

### Pinecone

```python
# Get index stats
stats = await pinecone.get_stats()
print(f"Total vectors: {stats['total_vectors']}")
print(f"Dimension: {stats['dimension']}")
print(f"Namespaces: {stats['namespaces']}")
```

---

## 🔒 Безопасность

1. **Secrets Management**
   - ✅ Все API ключи в `.env` (не коммитить!)
   - ✅ Используйте `SecretStr` из Pydantic
   - ⚠️ В production: AWS Secrets Manager / HashiCorp Vault

2. **Database**
   - ✅ SSL соединения в production
   - ✅ Ограниченные права пользователя БД
   - ✅ Regular backups

3. **R2**
   - ✅ Presigned URLs вместо public URLs
   - ✅ CORS настроен правильно
   - ✅ Lifecycle policies для старых файлов

---

## 🚧 Что дальше (Phase 2)

После завершения Database Foundation:

1. **Redis Cache Layer**
   - Semantic caching для LLM запросов
   - Session storage
   - Rate limiting

2. **Advanced Security**
   - Rate limiting middleware
   - Prompt injection detection
   - API key rotation

3. **Monitoring**
   - LangSmith integration
   - Prometheus metrics
   - Grafana dashboards

---

## ❓ Troubleshooting

### PostgreSQL connection failed
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql postgresql://user:password@localhost:5432/megaagent  # pragma: allowlist secret
```

### Pinecone "Index not found"
```python
# Pinecone index создается автоматически при первом использовании
# Убедитесь, что API key правильный:
from core.storage.pinecone_store import create_pinecone_store
store = create_pinecone_store()
# Index will be created automatically
```

### R2 403 Forbidden
```bash
# Проверьте R2 credentials
# Endpoint должен быть в формате:
# https://<account-id>.r2.cloudflarestorage.com
```

---

## 📞 Поддержка

- **Issues**: https://github.com/your-repo/issues
- **Documentation**: См. файлы в `docs/`
- **API Reference**: См. docstrings в коде

---

**Статус**: ✅ Phase 1 Complete - Ready for Testing
**Next**: Phase 2 - Redis Cache & Security Hardening
