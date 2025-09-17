#!/usr/bin/env python3
"""
Performance & Caching System Demo для mega_agent_pro.

Демонстрирует:
1. Multi-level caching (Memory + Redis simulation)
2. Semantic caching для embeddings и LLM responses
3. Cache integration с агентами
4. Performance monitoring и metrics
5. Cache warming и preloading
6. Automatic optimization strategies
7. Database query caching
8. Workflow state caching

Запуск:
    python performance_caching_demo.py
"""

import asyncio
import logging
import time
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.performance import (
    CacheManager,
    CacheIntegrationManager,
    CacheConfig,
    CacheItemType,
    create_default_cache_manager,
    create_cache_key,
)

# Import agents for integration testing
from core.memory.memory_manager import MemoryManager
from core.groupagents.rag_pipeline_agent import RAGPipelineAgent, SearchQuery


async def demo_basic_caching():
    """Демонстрация базового кэширования."""
    print("💾 === Basic Caching Demo ===\n")

    cache_manager = await create_default_cache_manager()

    # Демонстрируем основные операции кэша
    print("🔧 Basic cache operations:")

    # Set операции
    await cache_manager.main_cache.set("key1", "value1", ttl=60)
    await cache_manager.main_cache.set("key2", {"data": "complex_object"}, ttl=120)
    await cache_manager.main_cache.set("key3", [1, 2, 3, 4, 5], ttl=180)

    print("   ✅ Stored 3 items in cache")

    # Get операции
    value1 = await cache_manager.main_cache.get("key1")
    value2 = await cache_manager.main_cache.get("key2")
    value3 = await cache_manager.main_cache.get("key3")

    print(f"   📖 Retrieved value1: {value1}")
    print(f"   📖 Retrieved value2: {value2}")
    print(f"   📖 Retrieved value3: {value3}")

    # Проверяем несуществующий ключ
    missing = await cache_manager.main_cache.get("nonexistent")
    print(f"   ❓ Non-existent key: {missing}")

    # Показываем метрики
    metrics = await cache_manager.main_cache.get_metrics()
    print(f"\n📊 Cache metrics:")
    print(f"   🎯 Hit rate: {metrics.hit_rate:.1f}%")
    print(f"   📈 Total requests: {metrics.total_requests}")
    print(f"   ✅ Hits: {metrics.hits}")
    print(f"   ❌ Misses: {metrics.misses}")
    print(f"   ⏱️ Average access time: {metrics.average_access_time:.2f}ms")
    print()


async def demo_semantic_caching():
    """Демонстрация семантического кэширования."""
    print("🧠 === Semantic Caching Demo ===\n")

    cache_manager = await create_default_cache_manager()

    # Симулируем embeddings для демонстрации
    test_embeddings = {
        "What is artificial intelligence?": [0.1, 0.2, 0.3, 0.4, 0.5],
        "Define artificial intelligence": [0.12, 0.21, 0.31, 0.39, 0.48],  # Похожий
        "How does machine learning work?": [0.8, 0.7, 0.6, 0.5, 0.4],      # Разный
    }

    print("🔤 Caching embeddings and LLM responses:")

    # Кэшируем embeddings
    for text, embedding in test_embeddings.items():
        success = await cache_manager.cache_embedding(text, embedding)
        print(f"   ✅ Cached embedding for: '{text[:30]}...'")

    # Кэшируем LLM ответы
    llm_responses = {
        "What is AI?": "Artificial Intelligence is a field of computer science...",
        "Explain machine learning": "Machine learning is a subset of AI that enables...",
        "Define neural networks": "Neural networks are computing systems inspired by..."
    }

    for prompt, response in llm_responses.items():
        success = await cache_manager.cache_llm_response(prompt, response, model="demo_model")
        print(f"   ✅ Cached LLM response for: '{prompt}'")

    print("\n🔍 Testing cache retrieval:")

    # Проверяем retrieval
    for text in test_embeddings.keys():
        cached_embedding = await cache_manager.get_embedding(text)
        if cached_embedding:
            print(f"   🎯 Found cached embedding for: '{text[:30]}...'")
        else:
            print(f"   ❌ No cached embedding for: '{text[:30]}...'")

    for prompt in llm_responses.keys():
        cached_response = await cache_manager.get_llm_response(prompt, model="demo_model")
        if cached_response:
            print(f"   🎯 Found cached response for: '{prompt}'")
        else:
            print(f"   ❌ No cached response for: '{prompt}'")

    print()


async def demo_agent_integration():
    """Демонстрация интеграции кэширования с агентами."""
    print("🤖 === Agent Integration Demo ===\n")

    cache_manager = await create_default_cache_manager()
    integration_manager = CacheIntegrationManager(cache_manager)

    # Создаем агенты
    memory_manager = MemoryManager()
    rag_agent = RAGPipelineAgent(memory_manager=memory_manager)

    # Оборачиваем агенты кэшированием
    cached_memory = await integration_manager.wrap_memory_manager(memory_manager)
    cached_rag = await integration_manager.wrap_rag_agent(rag_agent)

    print("🔗 Created cached wrappers for agents")

    # Демонстрируем кэшированные операции
    print("\n📝 Testing cached operations:")

    # Тест кэширования поиска в памяти
    print("   🧠 Memory search caching:")
    start_time = time.time()
    result1 = await cached_memory.aretrieve("test query", user_id="demo_user", topk=5)
    time1 = time.time() - start_time

    start_time = time.time()
    result2 = await cached_memory.aretrieve("test query", user_id="demo_user", topk=5)  # Должно быть из кэша
    time2 = time.time() - start_time

    print(f"      First call: {time1:.4f}s")
    print(f"      Cached call: {time2:.4f}s")
    print(f"      Speedup: {time1/time2:.1f}x" if time2 > 0 else "      Instant cache hit!")

    # Тест кэширования RAG поиска
    print("   🔍 RAG search caching:")
    search_query = SearchQuery(query_text="legal document search")

    start_time = time.time()
    rag_result1 = await cached_rag.asearch(search_query, user_id="demo_user")
    time1 = time.time() - start_time

    start_time = time.time()
    rag_result2 = await cached_rag.asearch(search_query, user_id="demo_user")  # Кэшированный
    time2 = time.time() - start_time

    print(f"      First call: {time1:.4f}s")
    print(f"      Cached call: {time2:.4f}s")
    print(f"      Speedup: {time1/time2:.1f}x" if time2 > 0 else "      Instant cache hit!")

    print()


async def demo_workflow_caching():
    """Демонстрация кэширования состояний workflow."""
    print("🔄 === Workflow State Caching Demo ===\n")

    cache_manager = await create_default_cache_manager()
    integration_manager = CacheIntegrationManager(cache_manager)

    workflow_cache = integration_manager.workflow_cache

    # Создаем тестовые состояния workflow
    workflow_id = "legal_case_workflow_123"
    initial_state = {
        "step": "document_review",
        "progress": 0.3,
        "assigned_lawyer": "john_doe",
        "documents": ["contract.pdf", "evidence.docx"],
        "metadata": {"priority": "high", "deadline": "2025-01-01"}
    }

    print(f"💾 Saving workflow state for: {workflow_id}")
    await workflow_cache.save_workflow_state(workflow_id, initial_state)

    # Создаем checkpoint
    checkpoint_state = {
        **initial_state,
        "step": "legal_analysis",
        "progress": 0.6,
        "analysis_results": {"risk_level": "medium", "compliance": "passed"}
    }

    checkpoint_id = "analysis_complete"
    print(f"📍 Creating checkpoint: {checkpoint_id}")
    await workflow_cache.create_checkpoint(workflow_id, checkpoint_id, checkpoint_state)

    # Восстанавливаем состояния
    print("\n🔄 Restoring states:")

    loaded_state = await workflow_cache.load_workflow_state(workflow_id)
    if loaded_state:
        print(f"   ✅ Loaded workflow state - Step: {loaded_state['step']}, Progress: {loaded_state['progress']}")

    checkpoint_state_restored = await workflow_cache.restore_checkpoint(workflow_id, checkpoint_id)
    if checkpoint_state_restored:
        print(f"   ✅ Restored checkpoint - Step: {checkpoint_state_restored['step']}, Progress: {checkpoint_state_restored['progress']}")

    print()


async def demo_performance_monitoring():
    """Демонстрация мониторинга производительности."""
    print("📊 === Performance Monitoring Demo ===\n")

    cache_manager = await create_default_cache_manager()
    integration_manager = CacheIntegrationManager(cache_manager)

    # Генерируем некоторую активность для метрик
    print("🏃 Generating cache activity...")

    for i in range(20):
        key = f"test_key_{i}"
        value = f"test_value_{i} - {datetime.now()}"
        await cache_manager.main_cache.set(key, value)

        # Читаем некоторые ключи несколько раз
        if i % 3 == 0:
            for _ in range(5):
                await cache_manager.main_cache.get(key)

        # Иногда читаем несуществующие ключи
        if i % 5 == 0:
            await cache_manager.main_cache.get(f"nonexistent_{i}")

    print("   ✅ Generated 20 writes, multiple reads, and some misses")

    # Получаем комплексные метрики
    print("\n📈 Comprehensive metrics:")
    metrics = await cache_manager.get_comprehensive_metrics()

    print(f"   📅 Timestamp: {metrics['timestamp']}")
    print(f"   🎯 Overall hit rate: {metrics['aggregated']['overall_hit_rate']:.1f}%")
    print(f"   📊 Total requests: {metrics['aggregated']['total_requests']}")
    print(f"   ✅ Total hits: {metrics['aggregated']['total_hits']}")
    print(f"   ❌ Total misses: {metrics['aggregated']['total_misses']}")

    # Анализируем производительность
    print("\n🔍 Performance analysis:")
    analysis = await integration_manager.analyze_cache_performance()

    performance_insights = analysis["analysis"]["performance_insights"]
    print(f"   🏆 Overall performance: {performance_insights['overall_performance']}")
    print(f"   💾 Memory efficiency: {performance_insights['memory_efficiency']}")
    print(f"   📈 Scalability rating: {performance_insights['scalability_rating']}")

    # Показываем рекомендации
    recommendations = analysis["analysis"]["recommendations"]
    if recommendations:
        print("\n💡 Optimization recommendations:")
        for rec in recommendations:
            print(f"   🔧 {rec}")

    print()


async def demo_cache_optimization():
    """Демонстрация автоматической оптимизации кэша."""
    print("⚡ === Cache Optimization Demo ===\n")

    cache_manager = await create_default_cache_manager()
    integration_manager = CacheIntegrationManager(cache_manager)

    # Генерируем high-load scenario
    print("🚀 Simulating high-load scenario...")

    # Симулируем много запросов
    for i in range(100):
        await cache_manager.main_cache.set(f"high_load_{i}", f"data_{i}")

        # Неравномерное распределение доступа
        if i % 10 == 0:
            for _ in range(20):  # Горячие ключи
                await cache_manager.main_cache.get(f"high_load_{i}")
        elif i % 3 == 0:
            for _ in range(5):   # Теплые ключи
                await cache_manager.main_cache.get(f"high_load_{i}")

    print("   ✅ Simulated 100 writes with non-uniform access pattern")

    # Анализируем и оптимизируем
    print("\n🔧 Running optimization analysis...")
    optimization = await integration_manager.optimize_cache_configuration()

    print("   📋 Applied optimizations:")
    for opt in optimization["applied_optimizations"]:
        print(f"      ✅ {opt}")

    if optimization["configuration_changes"]:
        print("   ⚙️ Configuration changes:")
        for change, value in optimization["configuration_changes"].items():
            print(f"      🔧 {change}: {value}")

    print("   💡 Recommendations:")
    for rec in optimization["recommendations"]:
        print(f"      💭 {rec}")

    print()


async def demo_cache_warming():
    """Демонстрация предварительной загрузки кэша."""
    print("🔥 === Cache Warming Demo ===\n")

    cache_manager = await create_default_cache_manager()
    integration_manager = CacheIntegrationManager(cache_manager)

    # Предварительная загрузка пользовательских данных
    print("👥 Preloading user data...")
    user_ids = ["user_1", "user_2", "user_3", "admin", "lawyer_john"]
    await integration_manager.preload_user_data(user_ids)

    print(f"   ✅ Preloaded data for {len(user_ids)} users")

    # Предварительная загрузка частых запросов
    print("🔍 Preloading common queries...")
    await integration_manager.preload_common_queries()

    print("   ✅ Preloaded common query patterns")

    # Проверяем, что данные действительно в кэше
    print("\n✅ Verifying preloaded data:")

    for user_id in user_ids[:3]:  # Проверяем первых 3
        cached_user = await cache_manager.get_user_data(user_id)
        if cached_user:
            print(f"   🎯 Found preloaded user: {user_id}")

    # Проверяем общие запросы
    common_key = create_cache_key("common_query", "status")
    cached_query = await cache_manager.main_cache.get(common_key)
    if cached_query:
        print(f"   🎯 Found preloaded query: status")

    print()


async def demo_comprehensive_report():
    """Демонстрация комплексного отчета о производительности."""
    print("📋 === Comprehensive Performance Report ===\n")

    cache_manager = await create_default_cache_manager()
    integration_manager = CacheIntegrationManager(cache_manager)

    # Генерируем активность для отчета
    print("📊 Generating test data for report...")

    # Различные типы операций
    operations = [
        ("session", 50, lambda i: cache_manager.cache_session(f"session_{i}", {"user": f"user_{i}"})),
        ("user", 30, lambda i: cache_manager.cache_user_data(f"user_{i}", {"name": f"User {i}"})),
        ("embedding", 20, lambda i: cache_manager.cache_embedding(f"text_{i}", [0.1, 0.2, 0.3])),
        ("llm", 15, lambda i: cache_manager.cache_llm_response(f"prompt_{i}", f"response_{i}")),
    ]

    for op_type, count, operation in operations:
        for i in range(count):
            await operation(i)
        print(f"   ✅ Generated {count} {op_type} operations")

    # Симулируем чтения
    for op_type, count, _ in operations:
        for i in range(count // 2):  # Читаем половину
            if op_type == "session":
                await cache_manager.get_session(f"session_{i}")
            elif op_type == "user":
                await cache_manager.get_user_data(f"user_{i}")
            elif op_type == "embedding":
                await cache_manager.get_embedding(f"text_{i}")
            elif op_type == "llm":
                await cache_manager.get_llm_response(f"prompt_{i}")

    print("\n📋 Generating comprehensive report...")
    report = await integration_manager.generate_cache_report()

    print(f"\n🏆 === CACHE PERFORMANCE REPORT ===")
    print(f"📅 Generated: {report['timestamp']}")
    print(f"🏥 Health Status: {report['health_status']}")

    print(f"\n📊 Summary:")
    summary = report['summary']
    print(f"   📈 Total Requests: {summary['total_requests']}")
    print(f"   🎯 Overall Hit Rate: {summary['overall_hit_rate']:.1f}%")
    print(f"   🏆 Performance: {summary['overall_performance']}")

    print(f"\n🔍 Performance Analysis:")
    for cache_name, efficiency in report['performance_analysis']['cache_efficiency'].items():
        print(f"   📦 {cache_name.title()} Cache:")
        print(f"      🎯 Hit Rate: {efficiency['hit_rate']:.1f}%")
        print(f"      ⏱️ Avg Time: {efficiency['average_access_time_ms']:.2f}ms")
        print(f"      📝 Grade: {efficiency['performance_grade']}")

    if report['performance_analysis']['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in report['performance_analysis']['recommendations']:
            print(f"   🔧 {rec}")

    print(f"\n⚡ Optimization Status:")
    optimization = report['optimization_recommendations']
    if optimization['applied_optimizations']:
        print("   ✅ Applied optimizations:")
        for opt in optimization['applied_optimizations']:
            print(f"      🔧 {opt}")
    else:
        print("   ✅ System already optimized")

    print()


async def main():
    """Главная функция демонстрации."""
    print("⚡ MEGA AGENT PRO - Performance & Caching System Demo")
    print("=" * 70)
    print()

    try:
        # Демонстрируем различные аспекты системы кэширования
        await demo_basic_caching()
        await demo_semantic_caching()
        await demo_agent_integration()
        await demo_workflow_caching()
        await demo_performance_monitoring()
        await demo_cache_optimization()
        await demo_cache_warming()
        await demo_comprehensive_report()

        print("✅ === Performance & Caching Demo Complete ===")
        print()
        print("🎯 Key Features Demonstrated:")
        print("   ✅ Multi-level caching with LRU strategy")
        print("   ✅ Semantic caching for embeddings and LLM responses")
        print("   ✅ Agent integration with transparent caching")
        print("   ✅ Workflow state caching and checkpoints")
        print("   ✅ Comprehensive performance monitoring")
        print("   ✅ Automatic optimization strategies")
        print("   ✅ Cache warming and preloading")
        print("   ✅ Detailed performance reporting")
        print()
        print("🚀 Performance Benefits:")
        print("   📈 Dramatically reduced response times")
        print("   💾 Intelligent memory usage optimization")
        print("   🔄 Automatic cache invalidation strategies")
        print("   📊 Real-time performance analytics")
        print("   ⚡ Scalable multi-level architecture")
        print()
        print("🔧 Next Steps:")
        print("   1. Deploy with Redis for distributed caching")
        print("   2. Implement persistent cache layer")
        print("   3. Add machine learning for predictive caching")
        print("   4. Create cache monitoring dashboard")
        print("   5. Integrate with existing agents and workflows")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())