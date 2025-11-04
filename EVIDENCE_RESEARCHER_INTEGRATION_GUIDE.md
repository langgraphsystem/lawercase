# Evidence Researcher - Integration Guide

## Руководство по интеграции реальных API

Текущая реализация [EvidenceResearcher](core/workflows/eb1a/eb1a_workflow/evidence_researcher.py) использует симуляцию для демонстрации функционала. Это руководство описывает, как интегрировать реальные API для продакшн-использования.

---

## 📋 Содержание

1. [Web Search API Integration](#1-web-search-api-integration)
2. [LLM Integration for Data Extraction](#2-llm-integration-for-data-extraction)
3. [Caching Layer](#3-caching-layer)
4. [Rate Limiting & Retry Logic](#4-rate-limiting--retry-logic)
5. [Environment Configuration](#5-environment-configuration)
6. [Testing](#6-testing)

---

## 1. Web Search API Integration

### Опции Web Search API

#### Option A: Google Custom Search API

**Преимущества:**
- Высокое качество результатов
- Структурированные данные
- Google Knowledge Graph

**Ограничения:**
- 100 бесплатных запросов/день
- $5 за 1000 запросов после лимита

**Установка:**
```bash
pip install google-api-python-client
```

**Код замены:**

```python
# core/workflows/eb1a/eb1a_workflow/evidence_researcher.py

from googleapiclient.discovery import build
import os

class EvidenceResearcher:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.legal_precedents = self._initialize_precedents()

        # Initialize Google Search API
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        self.search_service = build(
            "customsearch", "v1",
            developerKey=self.google_api_key
        )

    async def _simulate_web_search(self, query: str) -> dict[str, Any]:
        """
        ЗАМЕНИТЬ НА: Real Google Custom Search API
        """
        try:
            # Execute search
            result = self.search_service.cse().list(
                q=query,
                cx=self.google_cse_id,
                num=10  # Number of results
            ).execute()

            # Convert to our format
            search_results = {
                "query": query,
                "results": [],
                "metadata": {
                    "total_results": int(result.get("searchInformation", {}).get("totalResults", 0)),
                    "search_time": float(result.get("searchInformation", {}).get("searchTime", 0))
                }
            }

            for item in result.get("items", []):
                search_results["results"].append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "displayLink": item.get("displayLink", "")
                })

            return search_results

        except Exception as e:
            print(f"Google Search API error: {e}")
            # Fallback to simulation if API fails
            return await self._simulate_web_search_fallback(query)
```

**Настройка Google Custom Search:**
1. Перейти на https://console.cloud.google.com/
2. Создать новый проект
3. Включить Custom Search API
4. Создать API ключ
5. Создать Custom Search Engine на https://cse.google.com/cse/
6. Получить CSE ID

**Environment Variables:**
```bash
# .env
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id
```

---

#### Option B: Bing Search API

**Преимущества:**
- Generous free tier (1000 транзакций/месяц)
- Хорошее качество результатов
- Простой API

**Установка:**
```bash
pip install azure-cognitiveservices-search-websearch
```

**Код замены:**

```python
from azure.cognitiveservices.search.websearch import WebSearchClient
from msrest.authentication import CognitiveServicesCredentials
import os

class EvidenceResearcher:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.legal_precedents = self._initialize_precedents()

        # Initialize Bing Search
        bing_api_key = os.getenv("BING_SEARCH_API_KEY")
        self.bing_client = WebSearchClient(
            endpoint="https://api.bing.microsoft.com/",
            credentials=CognitiveServicesCredentials(bing_api_key)
        )

    async def _simulate_web_search(self, query: str) -> dict[str, Any]:
        """
        ЗАМЕНИТЬ НА: Real Bing Search API
        """
        try:
            # Execute search
            result = self.bing_client.web.search(query=query, count=10)

            # Convert to our format
            search_results = {
                "query": query,
                "results": [],
                "metadata": {
                    "total_results": result.web_pages.total_estimated_matches if result.web_pages else 0,
                    "search_time": 0.5
                }
            }

            if result.web_pages:
                for page in result.web_pages.value:
                    search_results["results"].append({
                        "title": page.name,
                        "snippet": page.snippet,
                        "url": page.url,
                        "displayLink": page.display_url
                    })

            return search_results

        except Exception as e:
            print(f"Bing Search API error: {e}")
            return await self._simulate_web_search_fallback(query)
```

**Настройка Bing Search:**
1. Перейти на https://portal.azure.com/
2. Создать ресурс "Bing Search v7"
3. Получить API ключ

**Environment Variables:**
```bash
# .env
BING_SEARCH_API_KEY=your_bing_api_key_here
```

---

#### Option C: DuckDuckGo (Бесплатный)

**Преимущества:**
- Полностью бесплатный
- Без лимитов
- Приватный поиск

**Ограничения:**
- Менее структурированные результаты
- Может быть медленнее

**Установка:**
```bash
pip install duckduckgo-search
```

**Код замены:**

```python
from duckduckgo_search import DDGS

class EvidenceResearcher:
    async def _simulate_web_search(self, query: str) -> dict[str, Any]:
        """
        ЗАМЕНИТЬ НА: Real DuckDuckGo Search
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=10))

            search_results = {
                "query": query,
                "results": [],
                "metadata": {
                    "total_results": len(results),
                    "search_time": 0.5
                }
            }

            for item in results:
                search_results["results"].append({
                    "title": item.get("title", ""),
                    "snippet": item.get("body", ""),
                    "url": item.get("href", ""),
                    "displayLink": item.get("href", "").split("/")[2] if item.get("href") else ""
                })

            return search_results

        except Exception as e:
            print(f"DuckDuckGo Search error: {e}")
            return await self._simulate_web_search_fallback(query)
```

---

## 2. LLM Integration for Data Extraction

### Option A: OpenAI GPT-5

**Использование для structured data extraction:**

```python
from openai import AsyncOpenAI
import json
import os

class EvidenceResearcher:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.legal_precedents = self._initialize_precedents()

        # Initialize OpenAI
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

    async def _extract_org_profile(
        self, org_name: str, search_results: dict[str, Any]
    ) -> OrganizationProfile:
        """
        ЗАМЕНИТЬ НА: LLM-powered extraction
        """
        # Prepare context from search results
        context = self._format_search_context(search_results)

        # Create extraction prompt
        prompt = f"""Extract organization profile information from the following search results.

Organization Name: {org_name}

Search Results:
{context}

Extract the following information in JSON format:
{{
    "founded_year": int or null,
    "location": "string or null",
    "member_count": int or null,
    "acceptance_rate": float (0.0-1.0) or null,
    "mission_statement": "string or null",
    "notable_members": ["list of strings"],
    "media_mentions": int or null,
    "website": "string or null",
    "selectivity_indicators": ["list of strings"]
}}

Only include information you can verify from the search results. Use null for unknown fields.
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured information from web search results. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1000
            )

            # Parse JSON response
            extracted_data = json.loads(response.choices[0].message.content)

            # Create OrganizationProfile
            profile = OrganizationProfile(
                name=org_name,
                founded_year=extracted_data.get("founded_year"),
                location=extracted_data.get("location"),
                member_count=extracted_data.get("member_count"),
                acceptance_rate=extracted_data.get("acceptance_rate"),
                mission_statement=extracted_data.get("mission_statement"),
                notable_members=extracted_data.get("notable_members", []),
                media_mentions=extracted_data.get("media_mentions"),
                website=extracted_data.get("website"),
                selectivity_indicators=extracted_data.get("selectivity_indicators", []),
                metadata={
                    "research_date": datetime.utcnow().isoformat(),
                    "extraction_method": "gpt-5-mini",
                    "raw_search_results": search_results
                }
            )

            return profile

        except Exception as e:
            print(f"LLM extraction error: {e}")
            # Fallback to heuristic extraction
            return await self._extract_org_profile_fallback(org_name, search_results)

    def _format_search_context(self, search_results: dict[str, Any]) -> str:
        """Format search results for LLM prompt."""
        context_parts = []

        for i, result in enumerate(search_results.get("results", [])[:5], 1):
            context_parts.append(f"""
Result {i}:
Title: {result.get('title', 'N/A')}
URL: {result.get('url', 'N/A')}
Snippet: {result.get('snippet', 'N/A')}
""")

        return "\n".join(context_parts)
```

**Аналогично для CompetitionStats:**

```python
async def _extract_competition_stats(
    self, competition_name: str, year: int, search_results: dict[str, Any], context: str | None
) -> CompetitionStats:
    """
    ЗАМЕНИТЬ НА: LLM-powered extraction
    """
    search_context = self._format_search_context(search_results)

    prompt = f"""Extract competition statistics from the following search results.

Competition: {competition_name}
Year: {year}
Context: {context or 'N/A'}

Search Results:
{search_context}

Extract the following information in JSON format:
{{
    "total_entries": int or null,
    "total_winners": int or null,
    "acceptance_rate": float (0.0-1.0) or null,
    "geographic_scope": "local/national/international" or null,
    "jury_composition": ["list of strings"],
    "selection_criteria": ["list of strings"],
    "prize_value": "string or null",
    "previous_winners": ["list of strings"],
    "media_coverage": int or null,
    "organizing_body": "string or null"
}}
"""

    try:
        response = await self.openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "Extract structured competition data. Return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        data = json.loads(response.choices[0].message.content)

        stats = CompetitionStats(
            competition_name=competition_name,
            year=year,
            total_entries=data.get("total_entries"),
            total_winners=data.get("total_winners"),
            acceptance_rate=data.get("acceptance_rate"),
            geographic_scope=data.get("geographic_scope"),
            jury_composition=data.get("jury_composition", []),
            selection_criteria=data.get("selection_criteria", []),
            prize_value=data.get("prize_value"),
            previous_winners=data.get("previous_winners", []),
            media_coverage=data.get("media_coverage"),
            organizing_body=data.get("organizing_body"),
            metadata={
                "research_date": datetime.utcnow().isoformat(),
                "extraction_method": "gpt-5-mini"
            }
        )

        return stats

    except Exception as e:
        print(f"LLM extraction error: {e}")
        return await self._extract_competition_stats_fallback(competition_name, year, search_results, context)
```

**Environment Variables:**
```bash
# .env
OPENAI_API_KEY=your_openai_api_key_here
```

---

### Option B: Anthropic Claude

```python
from anthropic import AsyncAnthropic
import os

class EvidenceResearcher:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.legal_precedents = self._initialize_precedents()

        # Initialize Anthropic
        self.anthropic_client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    async def _extract_org_profile(
        self, org_name: str, search_results: dict[str, Any]
    ) -> OrganizationProfile:
        """LLM extraction with Claude."""
        context = self._format_search_context(search_results)

        prompt = f"""Extract organization profile from search results for: {org_name}

{context}

Return ONLY valid JSON with these fields:
{{"founded_year": int or null, "location": str or null, "member_count": int or null, ...}}
"""

        try:
            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            extracted_data = json.loads(message.content[0].text)

            profile = OrganizationProfile(
                name=org_name,
                **extracted_data,
                metadata={
                    "research_date": datetime.utcnow().isoformat(),
                    "extraction_method": "claude-3.5-sonnet"
                }
            )

            return profile

        except Exception as e:
            print(f"Claude extraction error: {e}")
            return await self._extract_org_profile_fallback(org_name, search_results)
```

**Environment Variables:**
```bash
# .env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

---

## 3. Caching Layer

**Добавление Redis cache для уменьшения API вызовов:**

```bash
pip install redis aioredis
```

```python
import redis.asyncio as redis
import json
import hashlib

class EvidenceResearcher:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.legal_precedents = self._initialize_precedents()

        # Initialize Redis cache
        self.cache = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )
        self.cache_ttl = 86400 * 7  # 7 days

    async def research_organization(
        self, org_name: str, context: str | None = None
    ) -> OrganizationProfile:
        """Research organization with caching."""
        # Generate cache key
        cache_key = self._generate_cache_key("org", org_name, context)

        # Try to get from cache
        cached = await self.cache.get(cache_key)
        if cached:
            print(f"Cache HIT for {org_name}")
            data = json.loads(cached)
            return OrganizationProfile(**data)

        print(f"Cache MISS for {org_name}")

        # Not in cache - do research
        search_query = f"{org_name} organization"
        if context:
            search_query += f" {context}"
        search_query += " founded members mission"

        search_results = await self._simulate_web_search(search_query)
        profile = await self._extract_org_profile(org_name, search_results)

        # Save to cache
        await self.cache.setex(
            cache_key,
            self.cache_ttl,
            profile.model_dump_json()
        )

        return profile

    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments."""
        key_data = f"{prefix}:" + ":".join(str(arg) for arg in args if arg)
        return hashlib.md5(key_data.encode()).hexdigest()
```

**Environment Variables:**
```bash
# .env
REDIS_URL=redis://localhost:6379
```

---

## 4. Rate Limiting & Retry Logic

**Добавление rate limiting и retry logic:**

```bash
pip install tenacity
```

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    """Simple rate limiter."""

    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window  # seconds
        self.calls = []

    async def acquire(self):
        """Wait if rate limit exceeded."""
        now = datetime.utcnow()

        # Remove old calls outside time window
        self.calls = [
            call_time for call_time in self.calls
            if (now - call_time).total_seconds() < self.time_window
        ]

        # Check if rate limit reached
        if len(self.calls) >= self.max_calls:
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call).total_seconds()
            if wait_time > 0:
                print(f"Rate limit reached. Waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)

        # Record this call
        self.calls.append(now)


class EvidenceResearcher:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.legal_precedents = self._initialize_precedents()

        # Rate limiters
        self.google_limiter = RateLimiter(max_calls=10, time_window=60)  # 10/min
        self.openai_limiter = RateLimiter(max_calls=50, time_window=60)  # 50/min

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    async def _simulate_web_search(self, query: str) -> dict[str, Any]:
        """Web search with rate limiting and retry."""
        # Rate limit
        await self.google_limiter.acquire()

        try:
            # Your actual API call here
            result = self.search_service.cse().list(
                q=query,
                cx=self.google_cse_id,
                num=10
            ).execute()

            # Process result...
            return search_results

        except Exception as e:
            print(f"Search API error (will retry): {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _extract_org_profile(
        self, org_name: str, search_results: dict[str, Any]
    ) -> OrganizationProfile:
        """LLM extraction with rate limiting and retry."""
        # Rate limit
        await self.openai_limiter.acquire()

        try:
            # Your LLM call here
            response = await self.openai_client.chat.completions.create(...)

            # Process response...
            return profile

        except Exception as e:
            print(f"LLM extraction error (will retry): {e}")
            raise
```

---

## 5. Environment Configuration

**Создайте `.env` файл:**

```bash
# .env.example

# Web Search API (choose one)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id

# OR
BING_SEARCH_API_KEY=your_bing_api_key_here

# LLM API (choose one)
OPENAI_API_KEY=your_openai_api_key_here

# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Caching (optional)
REDIS_URL=redis://localhost:6379

# Rate Limits
MAX_SEARCH_CALLS_PER_MINUTE=10
MAX_LLM_CALLS_PER_MINUTE=50
```

**Загрузка в коде:**

```python
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class EvidenceResearcher:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

        # Validate required env vars
        self._validate_config()

    def _validate_config(self):
        """Validate required environment variables."""
        required_vars = []

        # Check for at least one search API
        if not any([
            os.getenv("GOOGLE_API_KEY"),
            os.getenv("BING_SEARCH_API_KEY")
        ]):
            required_vars.append("Search API (GOOGLE_API_KEY or BING_SEARCH_API_KEY)")

        # Check for at least one LLM API
        if not any([
            os.getenv("OPENAI_API_KEY"),
            os.getenv("ANTHROPIC_API_KEY")
        ]):
            required_vars.append("LLM API (OPENAI_API_KEY or ANTHROPIC_API_KEY)")

        if required_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(required_vars)}"
            )
```

---

## 6. Testing

### Unit Tests with Mocking

```python
# tests/test_evidence_researcher_integration.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.workflows.eb1a.eb1a_workflow.evidence_researcher import (
    EvidenceResearcher,
    OrganizationProfile
)

@pytest.fixture
def researcher(memory_manager):
    return EvidenceResearcher(memory_manager)

@pytest.mark.asyncio
async def test_research_organization_with_google(researcher):
    """Test organization research with Google API."""
    with patch.object(researcher, 'search_service') as mock_service:
        # Mock Google API response
        mock_service.cse().list().execute.return_value = {
            "items": [
                {
                    "title": "IEEE Computer Society",
                    "snippet": "Founded in 1946, IEEE Computer Society has 85,000 members...",
                    "link": "https://www.computer.org"
                }
            ],
            "searchInformation": {
                "totalResults": "1000",
                "searchTime": 0.5
            }
        }

        # Execute
        profile = await researcher.research_organization("IEEE Computer Society")

        # Assertions
        assert profile.name == "IEEE Computer Society"
        assert profile.founded_year is not None
        assert profile.get_prestige_score() > 0

@pytest.mark.asyncio
async def test_llm_extraction_with_openai(researcher):
    """Test LLM extraction with OpenAI."""
    with patch.object(researcher, 'openai_client') as mock_client:
        # Mock OpenAI response
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(
                message=MagicMock(
                    content='{"founded_year": 1946, "member_count": 85000, "location": "USA"}'
                )
            )]
        ))

        # Execute
        search_results = {"query": "test", "results": []}
        profile = await researcher._extract_org_profile("IEEE", search_results)

        # Assertions
        assert profile.founded_year == 1946
        assert profile.member_count == 85000
```

### Integration Tests (with real APIs)

```python
# tests/integration/test_evidence_researcher_live.py

import pytest
import os

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_organization_research(researcher):
    """Test with REAL API calls (requires API keys)."""
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("Requires GOOGLE_API_KEY")

    profile = await researcher.research_organization("IEEE Computer Society")

    assert profile.name == "IEEE Computer Society"
    assert profile.founded_year is not None
    assert len(profile.selectivity_indicators) > 0
    assert profile.get_prestige_score() > 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_competition_research(researcher):
    """Test competition research with real APIs."""
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("Requires GOOGLE_API_KEY")

    stats = await researcher.research_competition_stats(
        "ACM Best Paper Award",
        year=2023,
        context="ACM SIGGRAPH"
    )

    assert stats.competition_name == "ACM Best Paper Award"
    assert stats.year == 2023
    assert stats.get_competitiveness_score() > 0
```

**Запуск тестов:**

```bash
# Unit tests only (with mocking)
pytest tests/test_evidence_researcher_integration.py

# Integration tests (requires API keys)
pytest tests/integration/test_evidence_researcher_live.py -m integration
```

---

## 🚀 Полный пример интеграции

**Полный файл с всеми интеграциями:**

```python
# core/workflows/eb1a/eb1a_workflow/evidence_researcher.py

from __future__ import annotations

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Web Search
from googleapiclient.discovery import build
# OR
# from azure.cognitiveservices.search.websearch import WebSearchClient
# from msrest.authentication import CognitiveServicesCredentials

# LLM
from openai import AsyncOpenAI
# OR
# from anthropic import AsyncAnthropic

# Caching
import redis.asyncio as redis

# Retry & Rate Limiting
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

from ....memory.memory_manager import MemoryManager

# Load environment
load_dotenv()


class EvidenceResearcher:
    """Production-ready Evidence Researcher with real API integrations."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.legal_precedents = self._initialize_precedents()

        # Validate config
        self._validate_config()

        # Initialize Google Search
        if os.getenv("GOOGLE_API_KEY"):
            self.search_service = build(
                "customsearch", "v1",
                developerKey=os.getenv("GOOGLE_API_KEY")
            )
            self.google_cse_id = os.getenv("GOOGLE_CSE_ID")

        # Initialize OpenAI
        if os.getenv("OPENAI_API_KEY"):
            self.openai_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )

        # Initialize Redis cache
        if os.getenv("REDIS_URL"):
            self.cache = redis.from_url(
                os.getenv("REDIS_URL"),
                decode_responses=True
            )
            self.cache_ttl = 86400 * 7  # 7 days
        else:
            self.cache = None

        # Rate limiters
        self.search_limiter = RateLimiter(
            max_calls=int(os.getenv("MAX_SEARCH_CALLS_PER_MINUTE", 10)),
            time_window=60
        )
        self.llm_limiter = RateLimiter(
            max_calls=int(os.getenv("MAX_LLM_CALLS_PER_MINUTE", 50)),
            time_window=60
        )

    def _validate_config(self):
        """Validate environment configuration."""
        # Implementation from section 5
        pass

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _web_search(self, query: str) -> dict[str, Any]:
        """Real web search with rate limiting and retry."""
        await self.search_limiter.acquire()

        # Google Search implementation
        result = self.search_service.cse().list(
            q=query,
            cx=self.google_cse_id,
            num=10
        ).execute()

        # Convert to standard format
        return self._convert_search_results(result)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _extract_with_llm(
        self, prompt: str, schema_description: str
    ) -> dict[str, Any]:
        """Extract structured data using LLM."""
        await self.llm_limiter.acquire()

        response = await self.openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "Extract structured data. Return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        return json.loads(response.choices[0].message.content)

    async def research_organization(
        self, org_name: str, context: str | None = None
    ) -> OrganizationProfile:
        """Research organization with full integration."""
        # Check cache
        if self.cache:
            cache_key = self._generate_cache_key("org", org_name, context)
            cached = await self.cache.get(cache_key)
            if cached:
                return OrganizationProfile(**json.loads(cached))

        # Web search
        query = f"{org_name} organization"
        if context:
            query += f" {context}"
        query += " founded members mission"

        search_results = await self._web_search(query)

        # LLM extraction
        profile_data = await self._extract_with_llm(
            self._build_org_extraction_prompt(org_name, search_results),
            OrganizationProfile.model_json_schema()
        )

        profile = OrganizationProfile(name=org_name, **profile_data)

        # Cache result
        if self.cache:
            await self.cache.setex(
                cache_key,
                self.cache_ttl,
                profile.model_dump_json()
            )

        return profile
```

---

## 📊 Cost Estimation

**Monthly costs for typical usage (1000 petitions/month):**

| Service | Free Tier | Paid Tier | Monthly Cost |
|---------|-----------|-----------|--------------|
| Google CSE | 100 calls/day | $5/1000 calls | ~$150 |
| Bing Search | 1000 calls/month | $7/1000 calls | ~$0-70 |
| DuckDuckGo | Unlimited | Free | $0 |
| OpenAI GPT-5-mini | - | $0.01/1K input, $0.03/1K output | ~$200 |
| Redis Cloud | 30MB free | $7/month | $0-7 |

**Рекомендация:**
- Development: DuckDuckGo + OpenAI (free search + $200/mo LLM)
- Production: Bing + OpenAI ($70 + $200 = $270/mo)
- High-volume: Google CSE + Claude ($150 + varies)

---

## 🔧 Troubleshooting

### Common Issues

**1. Rate Limit Errors**
```python
# Increase wait times in rate limiter
self.search_limiter = RateLimiter(max_calls=5, time_window=60)  # More conservative
```

**2. LLM Extraction Failures**
```python
# Add more detailed prompts and examples
# Use fallback to heuristic extraction
```

**3. Cache Connection Issues**
```python
# Add connection retry logic
# Gracefully degrade without cache
```

---

## 📚 Additional Resources

- [Google Custom Search API Docs](https://developers.google.com/custom-search/v1/overview)
- [Bing Search API Docs](https://learn.microsoft.com/en-us/bing/search-apis/)
- [OpenAI API Docs](https://platform.openai.com/docs/introduction)
- [Anthropic Claude API Docs](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [Redis Python Docs](https://redis-py.readthedocs.io/)

---

**Last Updated:** 2025-01-17
**Version:** 1.0.0
**Status:** Production Ready
