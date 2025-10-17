# Production Deployment Checklist

## Полный чеклист для развертывания MegaAgent в продакшн

---

## 📋 Overview

Этот документ содержит пошаговый чеклист для перевода MegaAgent Pro из режима разработки/демонстрации в полноценный продакшн.

**Текущий статус:** ✅ Development Ready, 🔶 Production Pending

**Основные компоненты для интеграции:**
1. WriterAgent - LLM для генерации секций
2. EvidenceResearcher - Web Search для исследований
3. Database - Production PostgreSQL
4. Caching - Redis
5. Monitoring - Logging & Metrics

---

## 1. Environment Setup

### 1.1 Environment Variables

**Создайте `.env` файл:**

```bash
# ================================
# Core Application
# ================================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# ================================
# Database (PostgreSQL)
# ================================
POSTGRES_DSN=postgresql+asyncpg://user:password@host:port/megaagent  # pragma: allowlist secret

# ================================
# LLM APIs
# ================================
# Option 1: OpenAI
OPENAI_API_KEY=sk-...  # pragma: allowlist secret
OPENAI_MODEL=gpt-4-turbo-preview

# Option 2: Anthropic (альтернатива)
ANTHROPIC_API_KEY=sk-ant-...  # pragma: allowlist secret
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# ================================
# Web Search APIs
# ================================
# Option 1: Google Custom Search
GOOGLE_API_KEY=AIza...  # pragma: allowlist secret
GOOGLE_CSE_ID=your_cse_id

# Option 2: Bing Search (альтернатива)
BING_SEARCH_API_KEY=your_bing_key  # pragma: allowlist secret

# Option 3: DuckDuckGo (бесплатная альтернатива, не требует ключа)

# ================================
# Caching
# ================================
REDIS_URL=redis://localhost:6379
CACHE_TTL=604800  # 7 days in seconds

# ================================
# Rate Limits
# ================================
MAX_SEARCH_CALLS_PER_MINUTE=10
MAX_LLM_CALLS_PER_MINUTE=50

# ================================
# Telegram Bot (optional)
# ================================
TELEGRAM_BOT_TOKEN=your_bot_token  # pragma: allowlist secret
TELEGRAM_ALLOWED_USERS=user1,user2,user3

# ================================
# Security
# ================================
SECRET_KEY=your_secret_key_here_min_32_chars  # pragma: allowlist secret
API_KEY=your_api_key  # pragma: allowlist secret

# ================================
# Monitoring
# ================================
SENTRY_DSN=https://...@sentry.io/...  # pragma: allowlist secret (optional)
```

**Checklist:**
- [ ] Создан `.env` файл
- [ ] Все чувствительные данные добавлены в `.env`
- [ ] `.env` добавлен в `.gitignore`
- [ ] Создан `.env.example` с примерами (без реальных ключей)
- [ ] Проверено, что `python-dotenv` установлен

---

## 2. API Integration

### 2.1 LLM Integration (WriterAgent)

**Файл:** [core/groupagents/writer_agent.py](core/groupagents/writer_agent.py)

**Checklist:**
- [ ] Установлен `openai>=1.0.0` или `anthropic>=0.18.0`
- [ ] API ключ добавлен в `.env`
- [ ] Заменён метод `_simulate_llm_generation()` на `_generate_with_gpt4()` или `_generate_with_claude()`
- [ ] Добавлена инициализация клиента в `__init__()`
- [ ] Протестирована генерация одной секции
- [ ] Добавлен error handling для API сбоев
- [ ] Настроен retry logic (tenacity)
- [ ] Добавлен rate limiting
- [ ] Протестирована стоимость генерации (cost tracking)

**Справка:** См. [WRITER_AGENT_LLM_INTEGRATION_GUIDE.md](WRITER_AGENT_LLM_INTEGRATION_GUIDE.md)

**Тестирование:**
```bash
# Test generation
python -c "
import asyncio
from core.groupagents.writer_agent import WriterAgent

async def test():
    writer = WriterAgent()
    section = await writer.agenerate_legal_section(
        section_type='awards',
        client_data={
            'beneficiary_name': 'Test',
            'field': 'AI',
            'evidence': [{'title': 'Test Award', 'description': 'Test'}]
        }
    )
    print(f'Generated: {section.word_count} words')
    print(f'Confidence: {section.confidence_score:.2f}')

asyncio.run(test())
"
```

---

### 2.2 Web Search Integration (EvidenceResearcher)

**Файл:** [core/workflows/eb1a/eb1a_workflow/evidence_researcher.py](core/workflows/eb1a/eb1a_workflow/evidence_researcher.py)

**Checklist:**
- [ ] Выбран Web Search API (Google/Bing/DuckDuckGo)
- [ ] Установлены зависимости:
  - Google: `google-api-python-client`
  - Bing: `azure-cognitiveservices-search-websearch`
  - DuckDuckGo: `duckduckgo-search`
- [ ] API ключ добавлен в `.env`
- [ ] Заменён метод `_simulate_web_search()` на реальный API call
- [ ] Добавлена LLM интеграция для data extraction
- [ ] Протестирован research для организации
- [ ] Протестирован research для конкурса
- [ ] Добавлен error handling
- [ ] Настроен rate limiting

**Справка:** См. [EVIDENCE_RESEARCHER_INTEGRATION_GUIDE.md](EVIDENCE_RESEARCHER_INTEGRATION_GUIDE.md)

**Тестирование:**
```bash
# Test organization research
python -c "
import asyncio
from core.workflows.eb1a.eb1a_workflow.evidence_researcher import EvidenceResearcher
from core.memory.memory_manager import MemoryManager

async def test():
    researcher = EvidenceResearcher(MemoryManager())
    profile = await researcher.research_organization('IEEE Computer Society')
    print(f'Founded: {profile.founded_year}')
    print(f'Prestige: {profile.get_prestige_score():.2f}')

asyncio.run(test())
"
```

---

## 3. Database Setup

### 3.1 PostgreSQL Production Database

**Checklist:**
- [ ] PostgreSQL 14+ установлен
- [ ] База данных создана (`megaagent`)
- [ ] Пользователь создан с правами
- [ ] Connection string добавлен в `.env`
- [ ] Запущены миграции Alembic
- [ ] Проверено соединение
- [ ] Настроены backups
- [ ] Настроен connection pooling

**Commands:**
```bash
# Create database
createdb megaagent

# Run migrations
alembic upgrade head

# Test connection
python -c "
import asyncio
from core.memory.memory_manager import MemoryManager

async def test():
    mm = MemoryManager()
    await mm.ainit()
    print('Database connected successfully')

asyncio.run(test())
"
```

---

### 3.2 Redis Cache

**Checklist:**
- [ ] Redis 6+ установлен и запущен
- [ ] Redis URL добавлен в `.env`
- [ ] Установлен `redis[asyncio]`
- [ ] Добавлена инициализация в EvidenceResearcher/WriterAgent
- [ ] Протестировано кэширование
- [ ] Настроен TTL (по умолчанию 7 дней)

**Commands:**
```bash
# Start Redis (Docker)
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# Windows: https://github.com/microsoftarchive/redis/releases
# Linux: sudo apt install redis-server
# macOS: brew install redis

# Test connection
redis-cli ping
# Should return: PONG

# Test from Python
python -c "
import asyncio
import redis.asyncio as redis

async def test():
    r = await redis.from_url('redis://localhost:6379')
    await r.set('test', 'hello')
    val = await r.get('test')
    print(f'Redis test: {val}')
    await r.close()

asyncio.run(test())
"
```

---

## 4. Dependencies

### 4.1 Production Requirements

**Проверьте `requirements.txt`:**

```txt
# Core
pydantic>=2.0.0
python-dotenv>=1.0.0
tenacity>=8.0.0

# Database
asyncpg>=0.29.0
alembic>=1.13.0
psycopg2-binary>=2.9.0

# Caching
redis[asyncio]>=5.0.0

# LLM APIs (choose one or both)
openai>=1.0.0
anthropic>=0.18.0

# Web Search (choose at least one)
google-api-python-client>=2.0.0  # Google
azure-cognitiveservices-search-websearch>=2.0.0  # Bing
duckduckgo-search>=5.0.0  # DuckDuckGo (free)

# Monitoring (optional)
sentry-sdk>=1.40.0

# Existing dependencies
# ... (keep all existing from requirements.txt)
```

**Checklist:**
- [ ] `requirements.txt` обновлён
- [ ] Все зависимости установлены: `pip install -r requirements.txt`
- [ ] Версии проверены и зафиксированы
- [ ] Создан `requirements-dev.txt` для dev dependencies
- [ ] Создан `requirements-prod.txt` для production-only

---

## 5. Testing

### 5.1 Unit Tests

**Checklist:**
- [ ] Все существующие тесты проходят
- [ ] Добавлены тесты для LLM integration (с моками)
- [ ] Добавлены тесты для Web Search (с моками)
- [ ] Протестирована валидация и retry logic
- [ ] Code coverage >= 80%

**Commands:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov-report=html

# Run only unit tests (no API calls)
pytest -m "not integration"
```

---

### 5.2 Integration Tests

**Checklist:**
- [ ] Тесты с реальными API написаны
- [ ] API ключи настроены для тестирования
- [ ] Созданы fixtures для повторяющихся данных
- [ ] Добавлены `@pytest.mark.integration` маркеры
- [ ] Тесты проходят с реальными API

**Commands:**
```bash
# Run integration tests (requires API keys)
pytest -m integration

# Run specific integration test
pytest tests/integration/test_writer_agent_live.py -v
```

---

### 5.3 End-to-End Testing

**Checklist:**
- [ ] Создан E2E тест полного EB-1A workflow
- [ ] Протестирован с реальными данными бенефициара
- [ ] Проверена генерация всех 10 критериев
- [ ] Проверено enrichment evidence
- [ ] Проверена финальная петиция

**Example E2E Test:**
```python
# tests/e2e/test_full_petition_workflow.py

import pytest
from core.workflows.eb1a.eb1a_coordinator import EB1ACoordinator

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_eb1a_petition():
    """Test complete EB-1A petition generation."""
    coordinator = EB1ACoordinator()

    # Prepare request
    request = EB1APetitionRequest(
        beneficiary_name="Dr. Test Beneficiary",
        field_of_expertise="Artificial Intelligence",
        primary_criteria=[
            EB1ACriterion.AWARDS,
            EB1ACriterion.MEMBERSHIP,
            EB1ACriterion.JUDGING
        ],
        # ... add evidence ...
    )

    # Generate petition
    petition = await coordinator.agenerate_petition(request)

    # Assertions
    assert petition.beneficiary_name == "Dr. Test Beneficiary"
    assert len(petition.sections) >= 3
    assert petition.overall_strength_score > 0.7
```

---

## 6. Security

### 6.1 Secrets Management

**Checklist:**
- [ ] Все секреты в `.env` файле
- [ ] `.env` в `.gitignore`
- [ ] Используется `python-dotenv` для загрузки
- [ ] В production используется secure secret manager:
  - AWS Secrets Manager
  - Azure Key Vault
  - HashiCorp Vault
  - Kubernetes Secrets
- [ ] API ключи ротируются регулярно
- [ ] Секреты не логируются

---

### 6.2 Input Validation

**Checklist:**
- [ ] Все входные данные валидируются Pydantic
- [ ] SQL injection защита (используется SQLAlchemy ORM)
- [ ] Rate limiting на API endpoints
- [ ] Max request size ограничен
- [ ] File upload validation (если используется)

---

### 6.3 Pre-commit Hooks

**Checklist:**
- [ ] `detect-secrets` hook активен
- [ ] `bandit` security scanner активен
- [ ] Все pre-commit hooks проходят
- [ ] False positives добавлены в allowlist

**Test:**
```bash
pre-commit run --all-files
```

---

## 7. Monitoring & Logging

### 7.1 Structured Logging

**Checklist:**
- [ ] Настроен structured logging (JSON format)
- [ ] Log levels корректно установлены (INFO в production)
- [ ] Sensitive data не логируется
- [ ] Ротация логов настроена
- [ ] Логи отправляются в centralized system (опционально):
  - CloudWatch (AWS)
  - Stackdriver (GCP)
  - Application Insights (Azure)
  - ELK Stack
  - Datadog

**Example logging config:**
```python
# config/logging.py

import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        return json.dumps(log_data)

# Configure logger
logger = logging.getLogger("megaagent")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

---

### 7.2 Error Tracking

**Checklist:**
- [ ] Sentry (или аналог) настроен
- [ ] DSN добавлен в `.env`
- [ ] Критические ошибки отправляются в Sentry
- [ ] Alerts настроены для критических ошибок
- [ ] Error grouping работает корректно

**Sentry Setup:**
```python
# app initialization
import sentry_sdk
import os

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        environment=os.getenv("ENVIRONMENT", "development"),
        traces_sample_rate=0.1  # 10% of transactions for performance monitoring
    )
```

---

### 7.3 Metrics & Analytics

**Checklist:**
- [ ] Добавлен tracking для ключевых метрик:
  - Количество сгенерированных секций
  - Средний confidence score
  - API call counts
  - Token usage
  - Costs (LLM, Search)
  - Error rates
  - Response times
- [ ] Dashboard создан для визуализации
- [ ] Alerts настроены для аномалий

**Metrics to track:**
```python
# Example metrics
{
    "sections_generated": {
        "total": 1000,
        "by_type": {"awards": 200, "press": 150, ...},
        "avg_confidence": 0.85,
        "avg_word_count": 350
    },
    "api_usage": {
        "llm_calls": 1000,
        "search_calls": 500,
        "cache_hit_rate": 0.65
    },
    "costs": {
        "llm_cost_usd": 30.50,
        "search_cost_usd": 10.00,
        "total_cost_usd": 40.50
    },
    "performance": {
        "avg_generation_time_ms": 2500,
        "p95_generation_time_ms": 4000,
        "error_rate": 0.02
    }
}
```

---

## 8. Performance Optimization

### 8.1 Caching Strategy

**Checklist:**
- [ ] Redis cache реализован
- [ ] TTL настроен (7 дней по умолчанию)
- [ ] Cache invalidation стратегия определена
- [ ] Высококачественные результаты кэшируются
- [ ] Cache hit rate мониторится (target: >60%)

---

### 8.2 Rate Limiting

**Checklist:**
- [ ] Rate limiting реализован для:
  - LLM API calls
  - Web Search API calls
  - Database queries (connection pooling)
- [ ] Limits настроены согласно API tier
- [ ] Retry logic с exponential backoff
- [ ] Rate limit errors логируются

---

### 8.3 Token Optimization

**Checklist:**
- [ ] Prompt optimization применён:
  - Ограничение примеров до 2-3
  - Truncate длинных описаний
  - Summarize patterns
- [ ] Token usage tracking включён
- [ ] Cost alerts настроены
- [ ] A/B тестирование разных prompt strategies

---

## 9. Deployment

### 9.1 Production Server

**Options:**

#### Option A: Docker Deployment

**Checklist:**
- [ ] `Dockerfile` создан
- [ ] `docker-compose.yml` настроен (app, postgres, redis)
- [ ] Environment variables передаются корректно
- [ ] Health checks добавлены
- [ ] Multi-stage build для уменьшения размера
- [ ] Протестирован локально

**Example `Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from core.memory.memory_manager import MemoryManager; asyncio.run(MemoryManager().ainit())"

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

#### Option B: Cloud Deployment (AWS/Azure/GCP)

**AWS Checklist:**
- [ ] EC2 instance или ECS/Fargate настроен
- [ ] RDS PostgreSQL создан
- [ ] ElastiCache Redis создан
- [ ] Security groups настроены
- [ ] Load balancer настроен (если нужно)
- [ ] Auto-scaling настроен
- [ ] CloudWatch logging включён
- [ ] IAM roles настроены

**Azure Checklist:**
- [ ] App Service или Container Instances
- [ ] Azure Database for PostgreSQL
- [ ] Azure Cache for Redis
- [ ] Application Insights для мониторинга
- [ ] Key Vault для секретов

**GCP Checklist:**
- [ ] Cloud Run или Compute Engine
- [ ] Cloud SQL PostgreSQL
- [ ] Memorystore Redis
- [ ] Cloud Logging
- [ ] Secret Manager

---

### 9.2 CI/CD Pipeline

**Checklist:**
- [ ] GitHub Actions / GitLab CI / Jenkins настроен
- [ ] Pipeline stages:
  - [ ] Linting (ruff, black)
  - [ ] Security scan (bandit, detect-secrets)
  - [ ] Unit tests
  - [ ] Integration tests (опционально)
  - [ ] Build Docker image
  - [ ] Deploy to staging
  - [ ] Deploy to production (manual approval)
- [ ] Secrets управляются через CI/CD secrets
- [ ] Deployment rollback стратегия

**Example GitHub Actions:**
```yaml
# .github/workflows/deploy.yml

name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t megaagent:latest .
      - name: Deploy to production
        run: |
          # Your deployment script here
          echo "Deploying to production..."
```

---

## 10. Documentation

### 10.1 User Documentation

**Checklist:**
- [ ] README.md обновлён с production instructions
- [ ] API documentation сгенерирована (Swagger/OpenAPI)
- [ ] User guide создан
- [ ] Примеры использования добавлены
- [ ] FAQ секция создана

---

### 10.2 Developer Documentation

**Checklist:**
- [ ] Architecture diagram обновлён
- [ ] Code comments актуальны
- [ ] Docstrings во всех public методах
- [ ] CONTRIBUTING.md создан
- [ ] Development setup guide актуален

---

## 11. Launch Checklist

### Pre-Launch

- [ ] Все unit tests проходят
- [ ] Все integration tests проходят
- [ ] E2E tests проходят
- [ ] Security audit выполнен
- [ ] Performance testing выполнено
- [ ] Load testing выполнено (если нужно)
- [ ] Backup strategy настроена
- [ ] Disaster recovery plan создан
- [ ] Monitoring dashboards настроены
- [ ] Alerts настроены
- [ ] Documentation завершена
- [ ] Stakeholder approval получен

### Launch Day

- [ ] Database migrations запущены
- [ ] Application deployed
- [ ] Health checks проходят
- [ ] Smoke tests проходят
- [ ] Monitoring активен
- [ ] Team standby для поддержки
- [ ] Rollback plan готов

### Post-Launch

- [ ] Мониторинг ошибок в течение 24 часов
- [ ] Performance метрики проверены
- [ ] User feedback собран
- [ ] Post-mortem meeting (если были проблемы)
- [ ] Documentation обновлена с lessons learned

---

## 12. Cost Management

### Monthly Cost Estimate (1000 petitions)

| Service | Provider | Estimated Cost |
|---------|----------|----------------|
| LLM API | OpenAI GPT-4 Turbo | $300-500 |
| Web Search | Bing Search API | $0-70 |
| Database | PostgreSQL (RDS/managed) | $50-200 |
| Redis Cache | ElastiCache/managed | $20-100 |
| Server | EC2/App Service | $50-200 |
| Monitoring | Sentry/Datadog | $0-100 |
| **Total** | | **$420-1170/month** |

**Optimization Tips:**
- Используйте DuckDuckGo вместо Bing/Google для search (бесплатно)
- Используйте Claude 3.5 Sonnet вместо GPT-4 (-10% cost)
- Включите aggressive caching (60%+ hit rate = -40% LLM costs)
- Используйте self-hosted Redis вместо managed (-70% cache cost)

**Checklist:**
- [ ] Budget установлен
- [ ] Cost alerts настроены
- [ ] Usage tracking включён
- [ ] Monthly reports автоматизированы
- [ ] Cost optimization review schedule

---

## 13. Support & Maintenance

### Support Plan

**Checklist:**
- [ ] On-call rotation определён
- [ ] Escalation process документирован
- [ ] Runbooks созданы для common issues
- [ ] Support contact определён
- [ ] SLA определён (если коммерческий)

### Maintenance Schedule

**Checklist:**
- [ ] Regular updates schedule
- [ ] Dependency updates plan
- [ ] Security patches процесс
- [ ] Database maintenance windows
- [ ] Backup verification schedule

---

## 📊 Final Checklist Summary

### Critical (Must Have)

- [ ] LLM API integration (WriterAgent)
- [ ] Environment variables configuration
- [ ] Database setup (PostgreSQL)
- [ ] All tests passing
- [ ] Security audit completed
- [ ] Monitoring & logging active

### High Priority

- [ ] Web Search API integration (EvidenceResearcher)
- [ ] Redis caching
- [ ] Rate limiting & retry logic
- [ ] Error tracking (Sentry)
- [ ] CI/CD pipeline
- [ ] Documentation complete

### Medium Priority

- [ ] Token optimization
- [ ] Cost tracking & alerts
- [ ] Performance optimization
- [ ] Load testing
- [ ] Advanced analytics dashboard

### Nice to Have

- [ ] A/B testing framework
- [ ] Advanced caching strategies
- [ ] Multi-region deployment
- [ ] Auto-scaling
- [ ] Advanced ML features

---

## 📞 Support

**Integration Guides:**
- [WriterAgent LLM Integration](WRITER_AGENT_LLM_INTEGRATION_GUIDE.md)
- [EvidenceResearcher Web Search Integration](EVIDENCE_RESEARCHER_INTEGRATION_GUIDE.md)
- [Architecture Overview](ARCHITECTURE_DIAGRAM.md)

**For Questions:**
- Documentation: Check docs in repository
- Issues: Create issue on GitHub
- Email: [Your support email]

---

## 🎯 Success Metrics

**Target KPIs for Production:**

| Metric | Target | Current |
|--------|--------|---------|
| Uptime | >99.5% | - |
| Error Rate | <2% | - |
| Avg Generation Time | <5s | - |
| Confidence Score | >0.80 | 0.84 ✅ |
| Cache Hit Rate | >60% | - |
| Cost per Petition | <$1.50 | - |
| User Satisfaction | >4.5/5 | - |

---

**Last Updated:** 2025-01-17
**Version:** 1.0.0
**Status:** Ready for Production Deployment

**Next Review:** 2025-02-17
