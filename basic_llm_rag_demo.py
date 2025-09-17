#!/usr/bin/env python3
"""
Basic LLM Router + Simple Embedder + RAG Foundation Demo для mega_agent_pro.

Демонстрирует:
1. LLM Router - интеллектуальную маршрутизацию между провайдерами
2. Simple Embedder - создание эмбеддингов с fallback механизмами
3. Basic RAG - полный RAG pipeline с поиском и генерацией
4. Интеграцию всех компонентов в единую систему
5. Различные стратегии обработки текстов

Запуск:
    python basic_llm_rag_demo.py
"""

import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.llm_router import (
    create_llm_router,
    LLMRequest,
    ModelType,
    Priority
)

from core.simple_embedder import (
    create_simple_embedder,
    EmbedRequest,
    EmbedProviderType
)

from core.basic_rag import (
    create_basic_rag,
    Document,
    RAGQuery,
    SearchType,
    ChunkingStrategy
)


async def llm_router_demo():
    """Демонстрация LLM Router"""
    print("🤖 === LLM Router Demo ===")

    # Конфигурация роутера
    router_config = {
        "routing_rules": {
            "model_preferences": {
                "chat": ["openai", "gemini", "claude", "mock"],
                "code": ["openai", "claude", "mock"],
                "vision": ["openai", "gemini"]
            }
        },
        "fallback_strategy": "round_robin",
        "load_balancing": True,
        "providers": {
            "openai": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "claude": {"enabled": True, "api_key": "demo-key"},
            "mock": {"enabled": True}
        }
    }

    # Создаем роутер
    router = await create_llm_router(router_config)

    print(f"   📊 Провайдеров настроено: {len(router.providers)}")

    # Проверяем здоровье провайдеров
    health = await router.health_check_all()
    healthy_count = sum(1 for is_healthy in health.values() if is_healthy)
    print(f"   🏥 Здоровых провайдеров: {healthy_count}/{len(health)}")

    # Тестируем различные типы запросов
    test_requests = [
        {
            "messages": [{"role": "user", "content": "Default chat request to test new models"}],
            "model_type": ModelType.CHAT,
            "priority": Priority.NORMAL
        },
        {
            "messages": [{"role": "user", "content": "Request for GPT-5 specifically"}],
            "model_type": ModelType.CHAT,
            "provider_preference": ["openai"]
        },
        {
            "messages": [{"role": "user", "content": "Request for Gemini 2.5 Pro specifically"}],
            "model_type": ModelType.CHAT,
            "provider_preference": ["gemini"]
        },
        {
            "messages": [{"role": "user", "content": "Request for Claude 4 Opus specifically"}],
            "model_type": ModelType.CHAT,
            "provider_preference": ["claude"]
        },
        {
            "messages": [{"role": "user", "content": "Write a Python function to calculate the factorial of a number"}],
            "model_type": ModelType.CODE,
            "priority": Priority.HIGH
        }
    ]

    print("\n   🔄 Тестируем маршрутизацию к новым моделям:")

    for i, request_data in enumerate(test_requests, 1):
        request = LLMRequest(**request_data)
        print(f"\n   --- Запрос {i}: {request.messages[0]['content']} ---")
        if request.provider_preference:
            print(f"   Provider Preference: {request.provider_preference}")
            
        response = await router.route_request(request)

        status_icon = "✅" if response.success else "❌"
        print(f"   {status_icon} Ответ от: {response.provider.value} ({response.model})")
        print(f"      Задержка: {response.latency:.2f}с, Токены: {response.tokens_used}")
        print(f"      Ответ: {response.content}")


    # Статистика провайдеров
    stats = await router.get_providers_stats()
    print(f"\n\n   📊 Итоговая статистика провайдеров:")

    for provider, provider_stats in stats.items():
        print(f"   📈 {provider}: {provider_stats.success_rate:.1f}% успех, "
              f"{provider_stats.total_requests} запросов, "
              f"сред. задержка: {provider_stats.average_latency:.2f}с")

    return router



async def simple_embedder_demo():
    """Демонстрация Simple Embedder"""
    print("\n🧠 === Simple Embedder Demo ===")

    # Конфигурация embedder
    embedder_config = {
        "default_provider": EmbedProviderType.OPENAI,
        "enable_cache": True,
        "cache_size": 1000,
        "providers": {
            "openai": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "local": {"enabled": True},
            "mock": {"enabled": True}
        }
    }

    # Создаем embedder
    embedder = await create_simple_embedder(embedder_config)

    print(f"   🔧 Провайдеров настроено: {len(embedder.providers)}")

    # Проверяем здоровье провайдеров
    health = await embedder.health_check_all()
    healthy_count = sum(1 for is_healthy in health.values() if is_healthy)
    print(f"   🏥 Здоровых провайдеров: {healthy_count}/{len(health)}")

    # Тестовые тексты
    test_texts = [
        "Машинное обучение - это подраздел искусственного интеллекта",
        "Python - популярный язык программирования для data science",
        "Векторные базы данных используются для семантического поиска",
        "Трансформеры изменили подход к обработке естественного языка",
        "RAG системы комбинируют поиск информации с генерацией текста"
    ]

    print(f"\n   🔄 Тестируем эмбеддинги для {len(test_texts)} текстов:")

    # Тестируем разных провайдеров
    for provider_type in [EmbedProviderType.OPENAI, EmbedProviderType.GEMINI, EmbedProviderType.LOCAL, EmbedProviderType.MOCK]:
        try:
            request = EmbedRequest(texts=test_texts[:2])  # Берем первые 2 для скорости
            response = await embedder.embed(request, provider_type)

            status_icon = "✅" if response.success else "❌"
            print(f"   {status_icon} {provider_type.value}: "
                  f"{len(response.embeddings)} векторов, dim={response.dimensions}")
            print(f"      Задержка: {response.latency:.3f}с, Стоимость: ${response.cost:.6f}")

        except Exception as e:
            print(f"   ❌ {provider_type.value}: Ошибка - {str(e)[:50]}...")

    # Тестируем кеширование
    print(f"\n   💾 Тестируем кеширование:")

    # Первый запрос
    request = EmbedRequest(texts=["Тест кеширования эмбеддингов"])
    response1 = await embedder.embed(request)
    print(f"   📝 Первый запрос: {response1.latency:.3f}с, кеш: {response1.cached}")

    # Повторный запрос (должен быть из кеша)
    response2 = await embedder.embed(request)
    print(f"   🔄 Повторный запрос: {response2.latency:.3f}с, кеш: {response2.cached}")

    # Статистика кеша
    cache_stats = embedder.get_cache_stats()
    print(f"   📊 Кеш: {cache_stats['size']}/{cache_stats['max_size']} записей")

    return embedder


async def basic_rag_demo(embedder=None, llm_router=None):
    """Демонстрация Basic RAG"""
    print("\n📚 === Basic RAG Demo ===")

    # Создаем RAG систему с интеграциями
    rag = await create_basic_rag(embedder, llm_router)

    print(f"   🏗️ RAG система создана")
    print(f"      Embedder: {'✅' if embedder else '❌'}")
    print(f"      LLM Router: {'✅' if llm_router else '❌'}")

    # Добавляем тестовые документы
    documents = [
        {
            "title": "Основы машинного обучения",
            "content": """
            Машинное обучение - это подраздел искусственного интеллекта, который позволяет компьютерам обучаться без явного программирования.
            Основные типы машинного обучения включают: обучение с учителем, обучение без учителя и обучение с подкреплением.

            Обучение с учителем использует размеченные данные для тренировки модели. Примеры включают классификацию и регрессию.
            Обучение без учителя работает с неразмеченными данными и включает кластеризацию и снижение размерности.
            Обучение с подкреплением основано на системе вознаграждений и наказаний.
            """,
            "metadata": {"category": "AI/ML", "difficulty": "beginner"}
        },
        {
            "title": "Python для Data Science",
            "content": """
            Python стал стандартом в области data science благодаря мощным библиотекам и простому синтаксису.
            Основные библиотеки включают: NumPy для численных вычислений, Pandas для работы с данными,
            Matplotlib и Seaborn для визуализации, Scikit-learn для машинного обучения.

            Jupyter Notebook обеспечивает интерактивную среду разработки, идеальную для исследовательского анализа данных.
            Pandas DataFrame - основная структура данных для анализа табличных данных.
            """,
            "metadata": {"category": "programming", "difficulty": "intermediate"}
        },
        {
            "title": "Векторные базы данных",
            "content": """
            Векторные базы данных специально разработаны для хранения и поиска высокоразмерных векторов.
            Они используются для семантического поиска, рекомендательных систем и RAG приложений.

            Популярные решения включают Pinecone, Weaviate, Chroma и FAISS.
            Векторные БД поддерживают различные алгоритмы поиска ближайших соседей: L2, косинусное расстояние, скалярное произведение.

            Индексирование векторов критически важно для производительности поиска в больших коллекциях.
            """,
            "metadata": {"category": "databases", "difficulty": "advanced"}
        },
        {
            "title": "RAG системы",
            "content": """
            RAG (Retrieval-Augmented Generation) - это подход, который комбинирует поиск релевантной информации
            с генерацией текста при помощи языковых моделей.

            RAG pipeline обычно включает: индексацию документов, векторный поиск, ранжирование результатов,
            формирование контекста и генерацию ответа.

            Преимущества RAG: актуальная информация, прозрачность источников, снижение галлюцинаций.
            RAG особенно эффективен для вопросно-ответных систем и поиска по корпоративным документам.
            """,
            "metadata": {"category": "AI/ML", "difficulty": "advanced"}
        }
    ]

    print(f"\n   📄 Индексируем {len(documents)} документов:")

    # Добавляем документы
    document_ids = []
    for doc in documents:
        doc_id = await rag.add_document(doc["title"], doc["content"], doc["metadata"])
        if doc_id:
            document_ids.append(doc_id)
            print(f"   ✅ {doc['title']}: {doc_id[:8]}...")
        else:
            print(f"   ❌ Ошибка индексации: {doc['title']}")

    # Статистика RAG
    stats = await rag.get_stats()
    print(f"\n   📊 RAG статистика:")
    print(f"      Документы: {stats['vector_store']['documents']}")
    print(f"      Части (chunks): {stats['vector_store']['total_chunks']}")
    print(f"      Эмбеддинги: {stats['vector_store']['total_embeddings']}")
    print(f"      Стратегия разбивки: {stats['chunking_strategy']}")

    # Тестируем различные типы поиска
    test_queries = [
        {
            "query": "Что такое машинное обучение?",
            "search_type": "semantic"
        },
        {
            "query": "Python библиотеки для анализа данных",
            "search_type": "semantic"
        },
        {
            "query": "векторные базы данных FAISS",
            "search_type": "keyword"
        },
        {
            "query": "Как работают RAG системы?",
            "search_type": "hybrid"
        }
    ]

    print(f"\n   🔍 Тестируем RAG запросы:")

    for i, test_query in enumerate(test_queries, 1):
        response = await rag.search(
            test_query["query"],
            max_results=3,
            search_type=test_query["search_type"]
        )

        status_icon = "✅" if response.success else "❌"
        print(f"\n   {status_icon} Запрос {i} ({test_query['search_type']}): {test_query['query']}")
        print(f"      Уверенность: {response.confidence:.2f}, Время: {response.latency:.2f}с")
        print(f"      Ответ: {response.answer[:100]}...")

        if response.sources:
            print(f"      Источники ({len(response.sources)}):")
            for j, source in enumerate(response.sources[:2], 1):
                print(f"        {j}. Релевантность: {source.score:.2f}")
                print(f"           {source.chunk.content[:80]}...")

    return rag


async def integration_demo():
    """Демонстрация полной интеграции всех компонентов"""
    print("\n🌟 === Integration Demo ===")

    print("🔄 Создаем интегрированную систему...")

    # Создаем все компоненты
    llm_router = await create_llm_router({
        "providers": {
            "openai": {"enabled": True},
            "gemini": {"enabled": True},
            "mock": {"enabled": True}
        }
    })

    embedder = await create_simple_embedder({
        "providers": {
            "openai": {"enabled": True},
            "gemini": {"enabled": True},
            "mock": {"enabled": True}
        }
    })

    # Создаем RAG с интеграциями
    rag = await create_basic_rag(embedder, llm_router)

    print("   ✅ Все компоненты интегрированы")

    # Сложный RAG workflow
    print("\n   🚀 Выполняем сложный RAG workflow:")

    # 1. Добавляем документ с юридической информацией
    legal_doc = """
    Трудовое право России регулирует отношения между работниками и работодателями.
    Основным документом является Трудовой кодекс РФ.

    Рабочее время не может превышать 40 часов в неделю для большинства категорий работников.
    Минимальный отпуск составляет 28 календарных дней.
    При увольнении работник должен отработать 2 недели, если договором не предусмотрено иное.

    Работодатель обязан выплачивать заработную плату не реже чем каждые полмесяца.
    При задержке зарплаты более чем на 15 дней работник может приостановить работу.
    """

    doc_id = await rag.add_document(
        "Основы трудового права РФ",
        legal_doc,
        {"domain": "legal", "jurisdiction": "RF"}
    )

    print(f"   📝 Документ добавлен: {doc_id[:8]}...")

    # 2. Комплексный запрос
    complex_query = "Сколько дней отпуска положено работнику и что делать при задержке зарплаты?"

    response = await rag.search(complex_query, max_results=5, search_type="hybrid")

    print(f"\n   🎯 Комплексный запрос: {complex_query}")
    print(f"   📊 Результат:")
    print(f"      Уверенность: {response.confidence:.2f}")
    print(f"      Время обработки: {response.latency:.2f}с")
    print(f"      Найдено источников: {len(response.sources)}")

    print(f"\n   💬 Ответ системы:")
    print(f"      {response.answer}")

    # 3. Проверяем работу всех компонентов
    print(f"\n   🔍 Проверка компонентов:")

    # LLM Router статистика
    llm_stats = await llm_router.get_providers_stats()
    active_llm_providers = sum(1 for stats in llm_stats.values() if stats.total_requests > 0)
    print(f"   🤖 LLM Router: {active_llm_providers} активных провайдеров")

    # Embedder статистика
    cache_stats = embedder.get_cache_stats()
    print(f"   🧠 Embedder: кеш содержит {cache_stats['size']} записей")

    # RAG статистика
    rag_stats = await rag.get_stats()
    print(f"   📚 RAG: {rag_stats['vector_store']['documents']} документов, "
          f"{rag_stats['vector_store']['total_chunks']} частей")

    return {"llm_router": llm_router, "embedder": embedder, "rag": rag}


async def main():
    """Главная функция демонстрации"""
    print("🚀 MEGA AGENT PRO - Basic LLM Router + Embedder + RAG Demo")
    print("=" * 70)

    try:
        # 1. Демонстрация LLM Router
        llm_router = await llm_router_demo()

        # 2. Демонстрация Simple Embedder
        embedder = await simple_embedder_demo()

        # 3. Демонстрация Basic RAG
        rag = await basic_rag_demo(embedder, llm_router)

        # 4. Полная интеграция
        components = await integration_demo()

        print("\n✅ === Demo Complete ===")

        print("\n🎯 Реализованные возможности:")
        print("   ✅ LLM Router с интеллектуальной маршрутизацией")
        print("      - Поддержка OpenAI, Gemini, Claude, Local моделей")
        print("      - Load balancing и failover")
        print("      - Rate limiting и cost optimization")
        print("      - Health monitoring и статистика")

        print("\n   ✅ Simple Embedder с multi-provider поддержкой")
        print("      - OpenAI, Gemini, Local Sentence Transformers")
        print("      - Кеширование для производительности")
        print("      - Fallback механизмы")
        print("      - Пакетная обработка")

        print("\n   ✅ Basic RAG с полным pipeline")
        print("      - Индексация документов с chunking")
        print("      - Семантический и keyword поиск")
        print("      - Гибридный поиск")
        print("      - Интеграция с LLM для генерации ответов")

        print("\n🚀 RAG Foundation готова для:")
        print("   📄 Обработки корпоративных документов")
        print("   🔍 Семантического поиска по знаниям")
        print("   💬 Интеллектуальных вопросно-ответных систем")
        print("   📚 Создания knowledge bases")
        print("   🏛️ Юридических и специализированных систем")

        print("\n🔧 Следующие шаги:")
        print("   1. Интеграция с реальными API ключами")
        print("   2. Добавление персистентного хранилища")
        print("   3. Расширение стратегий chunking")
        print("   4. Улучшение ранжирования результатов")
        print("   5. Добавление метрик качества RAG")

    except Exception as e:
        print(f"❌ Demo error: {e}")
        logger.exception("Demo failed")


if __name__ == "__main__":
    asyncio.run(main())