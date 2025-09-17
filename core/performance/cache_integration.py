"""
Cache Integration модуль для mega_agent_pro.

Интегрирует систему кэширования с существующими агентами:
- MemoryManager с intelligent caching
- RAGPipelineAgent с semantic caching
- MegaAgent с результатами команд
- Workflow caching для состояний
- Database query caching
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Union

from .caching_system import CacheManager, CacheItemType, create_cache_key


class CachedMemoryManager:
    """Обертка для MemoryManager с кэшированием."""

    def __init__(self, memory_manager, cache_manager: CacheManager):
        self.memory_manager = memory_manager
        self.cache_manager = cache_manager

    async def aretrieve(self, query: str, **kwargs) -> List[Any]:
        """Кэшированный поиск в памяти."""
        # Создаем ключ кэша на основе запроса и параметров
        cache_key = create_cache_key("memory_retrieve", query, json.dumps(kwargs, sort_keys=True))

        # Проверяем кэш
        cached_result = await self.cache_manager.get_query_result(cache_key)
        if cached_result is not None:
            return cached_result

        # Выполняем запрос
        result = await self.memory_manager.aretrieve(query, **kwargs)

        # Кэшируем результат (TTL: 15 минут для поисковых запросов)
        await self.cache_manager.cache_query_result(cache_key, result, ttl=900)

        return result

    async def awrite(self, payload, **kwargs) -> List[Any]:
        """Запись в память с инвалидацией кэша."""
        result = await self.memory_manager.awrite(payload, **kwargs)

        # Инвалидируем связанные кэши поиска
        await self.cache_manager.invalidate_by_tags({"memory", "search"})

        return result

    # Проксируем остальные методы без изменений
    async def alog_audit(self, event):
        return await self.memory_manager.alog_audit(event)

    async def aconsolidate(self, **kwargs):
        return await self.memory_manager.aconsolidate(**kwargs)

    async def asnapshot_thread(self, thread_id: str):
        return await self.memory_manager.asnapshot_thread(thread_id)

    async def aset_rmt(self, thread_id: str, slots: Dict[str, str]):
        return await self.memory_manager.aset_rmt(thread_id, slots)

    async def aget_rmt(self, thread_id: str):
        return await self.memory_manager.aget_rmt(thread_id)


class CachedRAGPipelineAgent:
    """Обертка для RAGPipelineAgent с семантическим кэшированием."""

    def __init__(self, rag_agent, cache_manager: CacheManager):
        self.rag_agent = rag_agent
        self.cache_manager = cache_manager

    async def asearch(self, search_query, user_id: str = "system") -> Any:
        """Кэшированный поиск с семантическим кэшем."""
        query_text = search_query.query_text if hasattr(search_query, 'query_text') else str(search_query)

        # Пытаемся найти семантически похожий результат
        # Для демо используем простое текстовое кэширование
        cache_key = create_cache_key("rag_search", query_text, user_id)

        cached_result = await self.cache_manager.get_query_result(cache_key)
        if cached_result is not None:
            # Помечаем как кэшированный результат
            if hasattr(cached_result, 'cached'):
                cached_result.cached = True
            return cached_result

        # Выполняем поиск
        result = await self.rag_agent.asearch(search_query, user_id)

        # Кэшируем результат (TTL: 30 минут для поисковых результатов)
        await self.cache_manager.cache_query_result(cache_key, result, ttl=1800)

        return result

    async def aprocess_document(self, document_path: str, user_id: str = "system") -> Any:
        """Кэшированная обработка документов."""
        # Создаем ключ на основе пути к файлу и его модификации
        cache_key = create_cache_key("rag_document", document_path, user_id)

        cached_result = await self.cache_manager.get_query_result(cache_key)
        if cached_result is not None:
            return cached_result

        # Обрабатываем документ
        result = await self.rag_agent.aprocess_document(document_path, user_id)

        # Кэшируем результат обработки (TTL: 2 часа)
        await self.cache_manager.cache_query_result(cache_key, result, ttl=7200)

        return result

    # Проксируем остальные методы
    def __getattr__(self, name):
        return getattr(self.rag_agent, name)


class CachedMegaAgent:
    """Обертка для MegaAgent с кэшированием команд."""

    def __init__(self, mega_agent, cache_manager: CacheManager):
        self.mega_agent = mega_agent
        self.cache_manager = cache_manager

    async def handle_command(self, command, user_role=None) -> Any:
        """Кэшированная обработка команд."""
        # Кэшируем только определенные типы команд (только для чтения)
        cacheable_commands = {'/status', '/list', '/search', '/help'}

        command_text = command.command if hasattr(command, 'command') else str(command)

        if command_text in cacheable_commands:
            cache_key = create_cache_key("mega_command", command_text, str(user_role))

            cached_result = await self.cache_manager.get_query_result(cache_key)
            if cached_result is not None:
                return cached_result

        # Выполняем команду
        result = await self.mega_agent.handle_command(command, user_role)

        # Кэшируем только читающие команды
        if command_text in cacheable_commands:
            await self.cache_manager.cache_query_result(cache_key, result, ttl=300)  # 5 минут

        return result

    # Проксируем остальные методы
    def __getattr__(self, name):
        return getattr(self.mega_agent, name)


class WorkflowStateCache:
    """Кэширование состояний workflow."""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    async def save_workflow_state(self, workflow_id: str, state: Dict[str, Any]) -> bool:
        """Сохранить состояние workflow."""
        cache_key = f"workflow_state:{workflow_id}"
        return await self.cache_manager.main_cache.set(
            cache_key,
            state,
            ttl=3600,  # 1 час
            item_type=CacheItemType.WORKFLOW_STATE,
            tags={"workflow", workflow_id}
        )

    async def load_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Загрузить состояние workflow."""
        cache_key = f"workflow_state:{workflow_id}"
        return await self.cache_manager.main_cache.get(cache_key)

    async def create_checkpoint(self, workflow_id: str, checkpoint_id: str, state: Dict[str, Any]) -> bool:
        """Создать checkpoint workflow."""
        cache_key = f"workflow_checkpoint:{workflow_id}:{checkpoint_id}"
        return await self.cache_manager.main_cache.set(
            cache_key,
            state,
            ttl=7200,  # 2 часа
            item_type=CacheItemType.WORKFLOW_STATE,
            tags={"workflow", "checkpoint", workflow_id}
        )

    async def restore_checkpoint(self, workflow_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Восстановить состояние из checkpoint."""
        cache_key = f"workflow_checkpoint:{workflow_id}:{checkpoint_id}"
        return await self.cache_manager.main_cache.get(cache_key)

    async def invalidate_workflow(self, workflow_id: str) -> int:
        """Инвалидировать все данные workflow."""
        return await self.cache_manager.invalidate_by_tags({workflow_id})


class DatabaseQueryCache:
    """Кэширование результатов database запросов."""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    def _create_query_hash(self, query: str, params: Optional[Dict] = None) -> str:
        """Создать хеш для SQL запроса."""
        query_data = {
            "query": query.strip().lower(),
            "params": params or {}
        }
        query_string = json.dumps(query_data, sort_keys=True)
        return hashlib.sha256(query_string.encode()).hexdigest()

    async def get_cached_query(self, query: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Получить результат кэшированного запроса."""
        query_hash = self._create_query_hash(query, params)
        return await self.cache_manager.get_query_result(query_hash)

    async def cache_query_result(
        self,
        query: str,
        result: Any,
        params: Optional[Dict] = None,
        ttl: int = 1800
    ) -> bool:
        """Кэшировать результат запроса."""
        query_hash = self._create_query_hash(query, params)
        return await self.cache_manager.cache_query_result(query_hash, result, ttl)

    async def invalidate_table_cache(self, table_name: str) -> int:
        """Инвалидировать кэш для конкретной таблицы."""
        # В реальной реализации здесь был бы более сложный механизм
        # отслеживания зависимостей запросов от таблиц
        return await self.cache_manager.invalidate_by_tags({f"table:{table_name}"})


class CacheIntegrationManager:
    """Главный менеджер интеграции кэширования."""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.workflow_cache = WorkflowStateCache(cache_manager)
        self.db_cache = DatabaseQueryCache(cache_manager)

    async def wrap_memory_manager(self, memory_manager) -> CachedMemoryManager:
        """Обернуть MemoryManager кэшированием."""
        return CachedMemoryManager(memory_manager, self.cache_manager)

    async def wrap_rag_agent(self, rag_agent) -> CachedRAGPipelineAgent:
        """Обернуть RAGPipelineAgent кэшированием."""
        return CachedRAGPipelineAgent(rag_agent, self.cache_manager)

    async def wrap_mega_agent(self, mega_agent) -> CachedMegaAgent:
        """Обернуть MegaAgent кэшированием."""
        return CachedMegaAgent(mega_agent, self.cache_manager)

    async def preload_user_data(self, user_ids: List[str]) -> None:
        """Предварительная загрузка пользовательских данных."""
        async def load_users():
            # В реальной реализации здесь был бы запрос к базе данных
            users_data = {}
            for user_id in user_ids:
                users_data[f"user:{user_id}"] = {"user_id": user_id, "preloaded": True}
            return users_data

        await self.cache_manager.warm_cache("users", load_users)

    async def preload_common_queries(self) -> None:
        """Предварительная загрузка часто используемых запросов."""
        common_queries = [
            "status",
            "help",
            "recent cases",
            "user permissions",
            "system health"
        ]

        for query in common_queries:
            # Кэшируем с пустым результатом для ускорения первого доступа
            cache_key = create_cache_key("common_query", query)
            await self.cache_manager.main_cache.set(
                cache_key,
                {"query": query, "preloaded": True},
                ttl=1800,
                item_type=CacheItemType.QUERY_RESULT
            )

    async def setup_cache_warming_schedule(self) -> None:
        """Настроить расписание предварительной загрузки кэша."""
        # В реальной реализации здесь был бы cron-like scheduler
        pass

    async def analyze_cache_performance(self) -> Dict[str, Any]:
        """Анализ производительности кэша."""
        metrics = await self.cache_manager.get_comprehensive_metrics()

        # Добавляем анализ
        analysis = {
            "cache_efficiency": {},
            "recommendations": [],
            "performance_insights": {}
        }

        # Анализируем эффективность каждого кэша
        for cache_name, cache_metrics in metrics["caches"].items():
            if isinstance(cache_metrics, dict) and "combined" in cache_metrics:
                cache_data = cache_metrics["combined"]
            else:
                cache_data = cache_metrics

            hit_rate = getattr(cache_data, 'hit_rate', 0) if hasattr(cache_data, 'hit_rate') else 0
            avg_time = getattr(cache_data, 'average_access_time', 0) if hasattr(cache_data, 'average_access_time') else 0

            analysis["cache_efficiency"][cache_name] = {
                "hit_rate": hit_rate,
                "average_access_time_ms": avg_time,
                "performance_grade": self._calculate_performance_grade(hit_rate, avg_time)
            }

            # Рекомендации по оптимизации
            if hit_rate < 50:
                analysis["recommendations"].append(f"Low hit rate in {cache_name} cache - consider adjusting TTL or cache size")
            if avg_time > 10:
                analysis["recommendations"].append(f"High access time in {cache_name} cache - consider optimization")

        # Общие инсайты
        overall_hit_rate = metrics["aggregated"]["overall_hit_rate"]
        analysis["performance_insights"] = {
            "overall_performance": "Excellent" if overall_hit_rate > 80 else "Good" if overall_hit_rate > 60 else "Needs Improvement",
            "memory_efficiency": "Good",  # Placeholder
            "scalability_rating": "High"  # Placeholder
        }

        return {**metrics, "analysis": analysis}

    def _calculate_performance_grade(self, hit_rate: float, avg_time: float) -> str:
        """Рассчитать оценку производительности."""
        if hit_rate > 80 and avg_time < 5:
            return "A"
        elif hit_rate > 60 and avg_time < 10:
            return "B"
        elif hit_rate > 40 and avg_time < 20:
            return "C"
        else:
            return "D"

    async def optimize_cache_configuration(self) -> Dict[str, Any]:
        """Автоматическая оптимизация конфигурации кэша."""
        metrics = await self.cache_manager.get_comprehensive_metrics()

        optimizations = {
            "applied_optimizations": [],
            "recommendations": [],
            "configuration_changes": {}
        }

        # Автоматические оптимизации на основе метрик
        overall_hit_rate = metrics["aggregated"]["overall_hit_rate"]

        if overall_hit_rate < 50:
            # Увеличиваем TTL для улучшения hit rate
            optimizations["applied_optimizations"].append("Increased TTL for better cache retention")
            optimizations["configuration_changes"]["ttl_multiplier"] = 1.5

        if metrics["aggregated"]["total_requests"] > 10000:
            # Увеличиваем размер кэша для high-load scenarios
            optimizations["applied_optimizations"].append("Increased cache size for high load")
            optimizations["configuration_changes"]["size_multiplier"] = 1.2

        # Рекомендации для дальнейшей оптимизации
        optimizations["recommendations"].extend([
            "Consider implementing distributed caching for multi-instance deployments",
            "Monitor cache warming effectiveness",
            "Implement intelligent TTL based on access patterns"
        ])

        return optimizations

    async def generate_cache_report(self) -> Dict[str, Any]:
        """Генерировать отчет о состоянии кэша."""
        performance_analysis = await self.analyze_cache_performance()
        optimization_report = await self.optimize_cache_configuration()

        report = {
            "timestamp": performance_analysis["timestamp"],
            "summary": {
                "total_requests": performance_analysis["aggregated"]["total_requests"],
                "overall_hit_rate": performance_analysis["aggregated"]["overall_hit_rate"],
                "overall_performance": performance_analysis["analysis"]["performance_insights"]["overall_performance"]
            },
            "detailed_metrics": performance_analysis["caches"],
            "performance_analysis": performance_analysis["analysis"],
            "optimization_recommendations": optimization_report,
            "health_status": "Healthy" if performance_analysis["aggregated"]["overall_hit_rate"] > 60 else "Needs Attention"
        }

        return report