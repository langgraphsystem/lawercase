#!/usr/bin/env python3
"""
Real Embeddings Integration Demo для mega_agent_pro.

Демонстрирует:
1. Инициализацию реальных embeddings providers
2. Интеграцию с MemoryManager
3. Сравнение производительности разных провайдеров
4. Кэширование и fallback механизмы
5. Использование в RAGPipelineAgent

Запуск:
    python real_embeddings_demo.py
"""

import asyncio
import logging
import os
import time
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверяем наличие необходимых модулей
try:
    from core.embeddings import (
        EmbeddingManager,
        EmbeddingRequest,
        create_gemini_config,
        create_local_config,
        create_openai_config,
    )
    from core.memory.memory_manager import MemoryManager
    from core.config import get_default_embedding_config, get_development_embedding_config
    EMBEDDINGS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Embeddings modules not available: {e}")
    EMBEDDINGS_AVAILABLE = False

from core.groupagents.rag_pipeline_agent import RAGPipelineAgent, SearchQuery
from core.memory.models import MemoryRecord


async def demo_embedding_providers():
    """Демонстрация работы различных embedding providers."""
    print("🔍 === DEMO: Real Embeddings Integration ===\n")

    if not EMBEDDINGS_AVAILABLE:
        print("❌ Real embeddings not available, skipping demo")
        return

    # Тестовые тексты
    test_texts = [
        "This is a legal document about contract law",
        "Artificial intelligence in legal research",
        "Database management for law firms",
        "Client confidentiality and data protection",
        "Regulatory compliance in financial services"
    ]

    print(f"📝 Test texts ({len(test_texts)} items):")
    for i, text in enumerate(test_texts, 1):
        print(f"   {i}. {text}")
    print()

    # 1. Демонстрация Local Provider
    await demo_local_embeddings(test_texts)

    # 2. Демонстрация Cloud Providers (если API keys доступны)
    await demo_cloud_embeddings(test_texts)

    # 3. Демонстрация интеграции с MemoryManager
    await demo_memory_integration(test_texts)

    # 4. Демонстрация кэширования
    await demo_caching_performance(test_texts)


async def demo_local_embeddings(test_texts: List[str]):
    """Демонстрация local embeddings."""
    print("🏠 === Local Embeddings Demo ===")

    try:
        # Создаем конфигурацию для локальной модели
        config = create_local_config()
        embedding_manager = EmbeddingManager([config])

        print(f"✅ Initialized local embedding provider: {config.model.value}")

        # Генерируем embeddings
        start_time = time.time()
        request = EmbeddingRequest(texts=test_texts)
        response = await embedding_manager.embed(request)
        elapsed = time.time() - start_time

        print(f"⚡ Generated {len(response.embeddings)} embeddings in {elapsed:.2f}s")
        print(f"📊 Embedding dimensions: {len(response.embeddings[0]) if response.embeddings else 0}")
        print(f"🔧 Provider: {response.provider}, Model: {response.model}")
        print(f"📈 Processing time: {response.processing_time:.3f}s")
        print(f"🎯 Token count: {response.token_count}")
        print()

    except Exception as e:
        print(f"❌ Local embeddings failed: {e}")
        print()


async def demo_cloud_embeddings(test_texts: List[str]):
    """Демонстрация cloud embeddings (если API keys доступны)."""
    print("☁️ === Cloud Embeddings Demo ===")

    # Проверяем Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        await demo_gemini_embeddings(test_texts, gemini_key)
    else:
        print("🔑 GEMINI_API_KEY not found, skipping Gemini demo")

    # Проверяем OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        await demo_openai_embeddings(test_texts, openai_key)
    else:
        print("🔑 OPENAI_API_KEY not found, skipping OpenAI demo")

    print()


async def demo_gemini_embeddings(test_texts: List[str], api_key: str):
    """Демонстрация Gemini embeddings."""
    try:
        config = create_gemini_config(api_key=api_key)
        embedding_manager = EmbeddingManager([config])

        print(f"✅ Initialized Gemini provider: {config.model.value}")

        start_time = time.time()
        request = EmbeddingRequest(texts=test_texts[:2])  # Меньше текстов для экономии API calls
        response = await embedding_manager.embed(request)
        elapsed = time.time() - start_time

        print(f"⚡ Gemini: {len(response.embeddings)} embeddings in {elapsed:.2f}s")
        print(f"📊 Dimensions: {len(response.embeddings[0]) if response.embeddings else 0}")

    except Exception as e:
        print(f"❌ Gemini embeddings failed: {e}")


async def demo_openai_embeddings(test_texts: List[str], api_key: str):
    """Демонстрация OpenAI embeddings."""
    try:
        config = create_openai_config(api_key=api_key)
        embedding_manager = EmbeddingManager([config])

        print(f"✅ Initialized OpenAI provider: {config.model.value}")

        start_time = time.time()
        request = EmbeddingRequest(texts=test_texts[:2])  # Меньше текстов для экономии API calls
        response = await embedding_manager.embed(request)
        elapsed = time.time() - start_time

        print(f"⚡ OpenAI: {len(response.embeddings)} embeddings in {elapsed:.2f}s")
        print(f"📊 Dimensions: {len(response.embeddings[0]) if response.embeddings else 0}")

    except Exception as e:
        print(f"❌ OpenAI embeddings failed: {e}")


async def demo_memory_integration(test_texts: List[str]):
    """Демонстрация интеграции с MemoryManager."""
    print("🧠 === MemoryManager Integration Demo ===")

    try:
        # Создаем MemoryManager с реальными embeddings
        embedding_configs = get_development_embedding_config()
        memory_manager = MemoryManager.create_with_real_embeddings(embedding_configs)

        print(f"✅ Created MemoryManager with {len(embedding_configs)} embedding providers")

        # Записываем тексты в память
        records = []
        for i, text in enumerate(test_texts):
            record = MemoryRecord(
                text=text,
                type="semantic",
                user_id="demo_user",
                metadata={"source": "demo", "index": i}
            )
            records.append(record)

        await memory_manager.awrite(records)
        print(f"📝 Stored {len(records)} records with embeddings")

        # Поиск похожих записей
        query = "legal document contract"
        results = await memory_manager.aretrieve(query, user_id="demo_user", topk=3)

        print(f"🔍 Search results for '{query}':")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result.text[:50]}... (score: {getattr(result, 'score', 'N/A')})")

        print()

    except Exception as e:
        print(f"❌ Memory integration failed: {e}")
        print()


async def demo_caching_performance(test_texts: List[str]):
    """Демонстрация производительности кэширования."""
    print("🚀 === Caching Performance Demo ===")

    if not EMBEDDINGS_AVAILABLE:
        print("❌ Embeddings not available for caching demo")
        return

    try:
        # Используем локальные embeddings для демонстрации кэширования
        config = create_local_config(cache_ttl_hours=1)
        embedding_manager = EmbeddingManager([config])

        # Первый запрос (без кэша)
        print("📊 First request (no cache):")
        start_time = time.time()
        request = EmbeddingRequest(texts=test_texts, cache_key="demo_cache_key")
        response1 = await embedding_manager.embed(request)
        time1 = time.time() - start_time

        print(f"   ⏱️ Time: {time1:.3f}s, Cached: {response1.cached}")

        # Второй запрос (с кэшом)
        print("📊 Second request (with cache):")
        start_time = time.time()
        request = EmbeddingRequest(texts=test_texts, cache_key="demo_cache_key")
        response2 = await embedding_manager.embed(request)
        time2 = time.time() - start_time

        print(f"   ⏱️ Time: {time2:.3f}s, Cached: {response2.cached}")

        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"🚀 Speedup: {speedup:.1f}x faster with cache")
        print()

    except Exception as e:
        print(f"❌ Caching demo failed: {e}")
        print()


async def demo_rag_integration():
    """Демонстрация интеграции с RAGPipelineAgent."""
    print("🔎 === RAG Pipeline Integration Demo ===")

    try:
        # Создаем MemoryManager с реальными embeddings
        if EMBEDDINGS_AVAILABLE:
            embedding_configs = get_development_embedding_config()
            memory_manager = MemoryManager.create_with_real_embeddings(embedding_configs)
            print(f"✅ Using real embeddings with {len(embedding_configs)} providers")
        else:
            memory_manager = MemoryManager()
            print("⚠️ Using mock embeddings (real embeddings not available)")

        # Создаем RAG агента
        rag_agent = RAGPipelineAgent(memory_manager=memory_manager)

        # Демонстрируем поиск
        search_query = SearchQuery(
            query_text="legal document management systems",
            limit=3
        )

        print(f"🔍 Searching for: '{search_query.query_text}'")
        search_response = await rag_agent.asearch(search_query, user_id="demo_user")

        print("📊 Search Results:")
        print(f"   Found: {len(search_response.results)} results")
        print(f"   Strategy: {search_response.strategy}")
        print(f"   Processing time: {search_response.processing_time:.3f}s")

        for i, result in enumerate(search_response.results, 1):
            print(f"   {i}. Score: {result.score:.3f}, Text: {result.text[:50]}...")

        print()

    except Exception as e:
        print(f"❌ RAG integration failed: {e}")
        print()


async def main():
    """Главная функция демонстрации."""
    print("🤖 MEGA AGENT PRO - Real Embeddings Integration Demo")
    print("=" * 60)
    print()

    # Демонстрируем embedding providers
    await demo_embedding_providers()

    # Демонстрируем интеграцию с RAG
    await demo_rag_integration()

    print("✅ === Demo Complete ===")
    print()
    print("💡 Next Steps:")
    print("   1. Set GEMINI_API_KEY environment variable for Gemini embeddings")
    print("   2. Set OPENAI_API_KEY environment variable for OpenAI embeddings")
    print("   3. Install sentence-transformers for local embeddings:")
    print("      pip install sentence-transformers")
    print("   4. Use real embeddings in production by calling:")
    print("      MemoryManager.create_with_real_embeddings(embedding_configs)")


if __name__ == "__main__":
    asyncio.run(main())