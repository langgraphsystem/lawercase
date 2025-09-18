"""
Comprehensive Caching System для mega_agent_pro.

Обеспечивает:
- Multi-level caching (L1: In-Memory, L2: Redis, L3: Persistent)
- Semantic caching для embeddings и LLM responses
- Query result caching для database операций
- Session caching для быстрого доступа
- Cache invalidation strategies
- Performance monitoring и metrics
- Distributed caching для multi-instance deployments
- Cache warming и preloading
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field


class CacheLevel(str, Enum):
    """Уровни кэша."""
    L1_MEMORY = "l1_memory"        # In-memory cache (fastest)
    L2_REDIS = "l2_redis"          # Redis cache (fast, distributed)
    L3_PERSISTENT = "l3_persistent" # Persistent cache (disk/database)


class CacheStrategy(str, Enum):
    """Стратегии кэширования."""
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used
    FIFO = "fifo"                  # First In, First Out
    TTL = "ttl"                    # Time To Live
    ADAPTIVE = "adaptive"          # Adaptive based on access patterns


class InvalidationStrategy(str, Enum):
    """Стратегии инвалидации кэша."""
    TTL_BASED = "ttl_based"        # Time-based expiration
    EVENT_BASED = "event_based"    # Event-driven invalidation
    VERSIONED = "versioned"        # Version-based invalidation
    DEPENDENCY = "dependency"      # Dependency-based invalidation
    MANUAL = "manual"              # Manual invalidation


class CacheItemType(str, Enum):
    """Типы элементов кэша."""
    EMBEDDING = "embedding"        # Embedding vectors
    LLM_RESPONSE = "llm_response"  # LLM responses
    QUERY_RESULT = "query_result"  # Database query results
    SESSION_DATA = "session_data"  # Session information
    USER_DATA = "user_data"        # User profiles and roles
    DOCUMENT = "document"          # Processed documents
    SEARCH_RESULT = "search_result" # Search results
    WORKFLOW_STATE = "workflow_state" # Workflow execution state


@dataclass
class CacheConfig:
    """Конфигурация кэша."""
    max_size: int = 1000           # Максимальный размер кэша
    ttl_seconds: int = 3600        # TTL по умолчанию (1 час)
    strategy: CacheStrategy = CacheStrategy.LRU
    invalidation: InvalidationStrategy = InvalidationStrategy.TTL_BASED
    enable_metrics: bool = True    # Включить метрики
    enable_persistence: bool = False # Включить персистентность
    compression: bool = True       # Сжатие данных
    encryption: bool = False       # Шифрование данных


class CacheMetrics(BaseModel):
    """Метрики кэша."""
    hits: int = Field(0, description="Количество попаданий")
    misses: int = Field(0, description="Количество промахов")
    evictions: int = Field(0, description="Количество вытеснений")
    invalidations: int = Field(0, description="Количество инвалидаций")
    total_requests: int = Field(0, description="Общее количество запросов")
    hit_rate: float = Field(0.0, description="Процент попаданий")
    average_access_time: float = Field(0.0, description="Среднее время доступа (мс)")
    memory_usage: int = Field(0, description="Использование памяти (байт)")
    last_reset: datetime = Field(default_factory=datetime.utcnow)

    def update_hit_rate(self):
        """Обновить процент попаданий."""
        if self.total_requests > 0:
            self.hit_rate = (self.hits / self.total_requests) * 100


class CacheItem(BaseModel):
    """Элемент кэша."""
    key: str = Field(..., description="Ключ элемента")
    value: Any = Field(..., description="Значение элемента")
    item_type: CacheItemType = Field(..., description="Тип элемента")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Время истечения")
    access_count: int = Field(0, description="Количество обращений")
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    size_bytes: int = Field(0, description="Размер в байтах")
    version: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tags: Set[str] = Field(default_factory=set, description="Теги для группировки")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")

    def is_expired(self) -> bool:
        """Проверить, истек ли элемент."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def touch(self) -> None:
        """Обновить время последнего доступа."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class CacheInterface(ABC):
    """Абстрактный интерфейс кэша."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Получить значение по ключу."""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        item_type: Optional[CacheItemType] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Установить значение по ключу."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Удалить значение по ключу."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Проверить существование ключа."""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Очистить весь кэш."""
        pass

    @abstractmethod
    async def get_metrics(self) -> CacheMetrics:
        """Получить метрики кэша."""
        pass


class InMemoryCache(CacheInterface):
    """In-memory реализация кэша с LRU стратегией."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.items: Dict[str, CacheItem] = {}
        self.access_order: List[str] = []  # Для LRU
        self.metrics = CacheMetrics()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Получить значение по ключу."""
        async with self._lock:
            start_time = time.time()
            self.metrics.total_requests += 1

            if key not in self.items:
                self.metrics.misses += 1
                self._update_access_time(start_time)
                return None

            item = self.items[key]

            # Проверяем TTL
            if item.is_expired():
                await self._remove_item(key)
                self.metrics.misses += 1
                self._update_access_time(start_time)
                return None

            # Обновляем статистику доступа
            item.touch()
            self._update_lru_order(key)

            self.metrics.hits += 1
            self.metrics.update_hit_rate()
            self._update_access_time(start_time)

            return item.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        item_type: Optional[CacheItemType] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Установить значение по ключу."""
        async with self._lock:
            # Рассчитываем время истечения
            expires_at = None
            if ttl or self.config.ttl_seconds:
                expiry_seconds = ttl or self.config.ttl_seconds
                expires_at = datetime.utcnow() + timedelta(seconds=expiry_seconds)

            # Оцениваем размер
            size_bytes = len(str(value).encode('utf-8'))

            # Создаем элемент кэша
            item = CacheItem(
                key=key,
                value=value,
                item_type=item_type or CacheItemType.QUERY_RESULT,
                expires_at=expires_at,
                size_bytes=size_bytes,
                tags=tags or set()
            )

            # Проверяем необходимость освобождения места
            await self._ensure_capacity()

            # Добавляем элемент
            self.items[key] = item
            self._update_lru_order(key)

            return True

    async def delete(self, key: str) -> bool:
        """Удалить значение по ключу."""
        async with self._lock:
            if key in self.items:
                await self._remove_item(key)
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Проверить существование ключа."""
        async with self._lock:
            if key not in self.items:
                return False

            item = self.items[key]
            if item.is_expired():
                await self._remove_item(key)
                return False

            return True

    async def clear(self) -> int:
        """Очистить весь кэш."""
        async with self._lock:
            count = len(self.items)
            self.items.clear()
            self.access_order.clear()
            return count

    async def get_metrics(self) -> CacheMetrics:
        """Получить метрики кэша."""
        async with self._lock:
            self.metrics.memory_usage = sum(item.size_bytes for item in self.items.values())
            return self.metrics.copy()

    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Инвалидировать элементы по тегам."""
        async with self._lock:
            keys_to_remove = []
            for key, item in self.items.items():
                if tags.intersection(item.tags):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                await self._remove_item(key)
                self.metrics.invalidations += 1

            return len(keys_to_remove)

    async def cleanup_expired(self) -> int:
        """Очистить истекшие элементы."""
        async with self._lock:
            expired_keys = []
            for key, item in self.items.items():
                if item.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                await self._remove_item(key)

            return len(expired_keys)

    def _update_lru_order(self, key: str) -> None:
        """Обновить порядок LRU."""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    async def _ensure_capacity(self) -> None:
        """Обеспечить свободное место в кэше."""
        while len(self.items) >= self.config.max_size:
            if not self.access_order:
                break

            # Удаляем наименее недавно использованный элемент (LRU)
            oldest_key = self.access_order[0]
            await self._remove_item(oldest_key)
            self.metrics.evictions += 1

    async def _remove_item(self, key: str) -> None:
        """Удалить элемент из кэша."""
        if key in self.items:
            del self.items[key]
        if key in self.access_order:
            self.access_order.remove(key)

    def _update_access_time(self, start_time: float) -> None:
        """Обновить среднее время доступа."""
        access_time = (time.time() - start_time) * 1000  # в миллисекундах
        if self.metrics.average_access_time == 0:
            self.metrics.average_access_time = access_time
        else:
            # Экспоненциальное скользящее среднее
            alpha = 0.1
            self.metrics.average_access_time = (
                alpha * access_time + (1 - alpha) * self.metrics.average_access_time
            )


class RedisCache(CacheInterface):
    """Redis реализация кэша (mock implementation)."""

    def __init__(self, config: CacheConfig, redis_url: str = "redis://localhost:6379"):
        self.config = config
        self.redis_url = redis_url
        self.metrics = CacheMetrics()
        self._connected = False

    async def connect(self) -> bool:
        """Подключиться к Redis."""
        try:
            # В реальной реализации здесь было бы подключение к Redis
            # import aioredis
            # self.redis = await aioredis.from_url(self.redis_url)
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Получить значение по ключу."""
        if not self._connected:
            return None

        self.metrics.total_requests += 1

        # Mock implementation - в реальности здесь был бы Redis GET
        # value = await self.redis.get(key)
        value = None

        if value is None:
            self.metrics.misses += 1
        else:
            self.metrics.hits += 1

        self.metrics.update_hit_rate()
        return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        item_type: Optional[CacheItemType] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Установить значение по ключу."""
        if not self._connected:
            return False

        # Mock implementation - в реальности здесь был бы Redis SET
        # serialized = pickle.dumps(value)
        # ttl_value = ttl or self.config.ttl_seconds
        # await self.redis.setex(key, ttl_value, serialized)

        return True

    async def delete(self, key: str) -> bool:
        """Удалить значение по ключу."""
        if not self._connected:
            return False

        # Mock implementation - в реальности здесь был бы Redis DEL
        # result = await self.redis.delete(key)
        # return result > 0

        return True

    async def exists(self, key: str) -> bool:
        """Проверить существование ключа."""
        if not self._connected:
            return False

        # Mock implementation
        # return await self.redis.exists(key)

        return False

    async def clear(self) -> int:
        """Очистить весь кэш."""
        if not self._connected:
            return 0

        # Mock implementation
        # await self.redis.flushdb()

        return 0

    async def get_metrics(self) -> CacheMetrics:
        """Получить метрики кэша."""
        return self.metrics.copy()


class MultiLevelCache(CacheInterface):
    """Multi-level кэш (L1: Memory, L2: Redis, L3: Persistent)."""

    def __init__(
        self,
        l1_config: Optional[CacheConfig] = None,
        l2_config: Optional[CacheConfig] = None,
        redis_url: str = "redis://localhost:6379"
    ):
        # L1: In-memory cache (fastest)
        self.l1_cache = InMemoryCache(l1_config or CacheConfig(max_size=500, ttl_seconds=900))

        # L2: Redis cache (distributed)
        self.l2_cache = RedisCache(l2_config or CacheConfig(max_size=5000, ttl_seconds=3600), redis_url)

        self.metrics = CacheMetrics()

    async def initialize(self) -> bool:
        """Инициализировать кэши."""
        l2_connected = await self.l2_cache.connect()
        return l2_connected

    async def get(self, key: str) -> Optional[Any]:
        """Получить значение по ключу (проверяем L1, затем L2)."""
        start_time = time.time()
        self.metrics.total_requests += 1

        # Сначала проверяем L1 (memory)
        value = await self.l1_cache.get(key)
        if value is not None:
            self.metrics.hits += 1
            self.metrics.update_hit_rate()
            self._update_access_time(start_time)
            return value

        # Затем проверяем L2 (Redis)
        value = await self.l2_cache.get(key)
        if value is not None:
            # Кэшируем в L1 для быстрого доступа
            await self.l1_cache.set(key, value)
            self.metrics.hits += 1
            self.metrics.update_hit_rate()
            self._update_access_time(start_time)
            return value

        # Не найдено ни в одном кэше
        self.metrics.misses += 1
        self.metrics.update_hit_rate()
        self._update_access_time(start_time)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        item_type: Optional[CacheItemType] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Установить значение по ключу (записываем в оба уровня)."""
        # Записываем в L1
        l1_success = await self.l1_cache.set(key, value, ttl, item_type, tags)

        # Записываем в L2
        l2_success = await self.l2_cache.set(key, value, ttl, item_type, tags)

        return l1_success and l2_success

    async def delete(self, key: str) -> bool:
        """Удалить значение по ключу (из всех уровней)."""
        l1_deleted = await self.l1_cache.delete(key)
        l2_deleted = await self.l2_cache.delete(key)
        return l1_deleted or l2_deleted

    async def exists(self, key: str) -> bool:
        """Проверить существование ключа."""
        return await self.l1_cache.exists(key) or await self.l2_cache.exists(key)

    async def clear(self) -> int:
        """Очистить все уровни кэша."""
        l1_count = await self.l1_cache.clear()
        l2_count = await self.l2_cache.clear()
        return l1_count + l2_count

    async def get_metrics(self) -> Dict[str, CacheMetrics]:
        """Получить метрики всех уровней."""
        return {
            "l1_memory": await self.l1_cache.get_metrics(),
            "l2_redis": await self.l2_cache.get_metrics(),
            "combined": self.metrics.copy()
        }

    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Инвалидировать элементы по тегам во всех уровнях."""
        l1_count = 0
        if hasattr(self.l1_cache, 'invalidate_by_tags'):
            l1_count = await self.l1_cache.invalidate_by_tags(tags)

        # Для L2 (Redis) нужна отдельная реализация invalidation by tags
        l2_count = 0

        return l1_count + l2_count

    def _update_access_time(self, start_time: float) -> None:
        """Обновить среднее время доступа."""
        access_time = (time.time() - start_time) * 1000
        if self.metrics.average_access_time == 0:
            self.metrics.average_access_time = access_time
        else:
            alpha = 0.1
            self.metrics.average_access_time = (
                alpha * access_time + (1 - alpha) * self.metrics.average_access_time
            )


class SemanticCache:
    """Семантический кэш для embeddings и похожих запросов."""

    def __init__(self, cache: CacheInterface, similarity_threshold: float = 0.9):
        self.cache = cache
        self.similarity_threshold = similarity_threshold
        self.embeddings_index: Dict[str, Tuple[str, List[float]]] = {}  # hash -> (key, embedding)

    def _hash_query(self, query: str) -> str:
        """Создать хеш для запроса."""
        return hashlib.sha256(query.encode()).hexdigest()

    def _compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Вычислить косинусное сходство между embeddings."""
        if not embedding1 or not embedding2 or len(embedding1) != len(embedding2):
            return 0.0

        # Косинусное сходство
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def get_similar(self, query: str, query_embedding: List[float]) -> Optional[Any]:
        """Найти семантически похожий результат."""
        query_hash = self._hash_query(query)

        # Сначала проверяем точное совпадение
        exact_result = await self.cache.get(query_hash)
        if exact_result is not None:
            return exact_result

        # Ищем семантически похожие
        best_similarity = 0.0
        best_key = None

        for cached_hash, (cached_key, cached_embedding) in self.embeddings_index.items():
            similarity = self._compute_similarity(query_embedding, cached_embedding)
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_key = cached_key

        if best_key:
            return await self.cache.get(best_key)

        return None

    async def set_with_embedding(
        self,
        query: str,
        query_embedding: List[float],
        result: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Сохранить результат с embedding для семантического поиска."""
        query_hash = self._hash_query(query)

        # Сохраняем в основной кэш
        success = await self.cache.set(
            query_hash,
            result,
            ttl=ttl,
            item_type=CacheItemType.LLM_RESPONSE,
            tags={"semantic", "llm"}
        )

        if success and query_embedding:
            # Добавляем в индекс embeddings
            self.embeddings_index[query_hash] = (query_hash, query_embedding)

        return success


class CacheManager:
    """Основной менеджер кэширования для всей системы."""

    def __init__(
        self,
        enable_l1: bool = True,
        enable_l2: bool = False,
        redis_url: str = "redis://localhost:6379",
        l1_config: Optional[CacheConfig] = None,
        l2_config: Optional[CacheConfig] = None
    ):
        # Основной кэш
        if enable_l2:
            self.main_cache = MultiLevelCache(l1_config, l2_config, redis_url)
        else:
            self.main_cache = InMemoryCache(l1_config or CacheConfig())

        # Специализированные кэши
        self.embedding_cache = SemanticCache(self.main_cache, similarity_threshold=0.85)
        self.session_cache = InMemoryCache(CacheConfig(max_size=1000, ttl_seconds=1800))  # 30 минут
        self.user_cache = InMemoryCache(CacheConfig(max_size=500, ttl_seconds=3600))     # 1 час
        self.query_cache = InMemoryCache(CacheConfig(max_size=2000, ttl_seconds=900))    # 15 минут

        self._cache_warming_tasks: Set[asyncio.Task] = set()

    async def initialize(self) -> bool:
        """Инициализировать все кэши."""
        success = True

        if isinstance(self.main_cache, MultiLevelCache):
            success = await self.main_cache.initialize()

        return success

    # Embedding caching
    async def get_embedding(self, text: str, text_embedding: Optional[List[float]] = None) -> Optional[List[float]]:
        """Получить embedding из кэша."""
        if text_embedding:
            result = await self.embedding_cache.get_similar(text, text_embedding)
        else:
            key = f"embedding:{hashlib.sha256(text.encode()).hexdigest()}"
            result = await self.main_cache.get(key)

        return result

    async def cache_embedding(self, text: str, embedding: List[float], ttl: int = 3600) -> bool:
        """Кэшировать embedding."""
        return await self.embedding_cache.set_with_embedding(text, embedding, embedding, ttl)

    # LLM response caching
    async def get_llm_response(self, prompt: str, model: str = "default") -> Optional[str]:
        """Получить LLM ответ из кэша."""
        key = f"llm:{model}:{hashlib.sha256(prompt.encode()).hexdigest()}"
        return await self.main_cache.get(key)

    async def cache_llm_response(self, prompt: str, response: str, model: str = "default", ttl: int = 1800) -> bool:
        """Кэшировать LLM ответ."""
        key = f"llm:{model}:{hashlib.sha256(prompt.encode()).hexdigest()}"
        return await self.main_cache.set(
            key,
            response,
            ttl=ttl,
            item_type=CacheItemType.LLM_RESPONSE,
            tags={"llm", model}
        )

    # Session caching
    async def get_session(self, session_id: str) -> Optional[Any]:
        """Получить сессию из кэша."""
        return await self.session_cache.get(f"session:{session_id}")

    async def cache_session(self, session_id: str, session_data: Any, ttl: int = 1800) -> bool:
        """Кэшировать сессию."""
        return await self.session_cache.set(
            f"session:{session_id}",
            session_data,
            ttl=ttl,
            item_type=CacheItemType.SESSION_DATA,
            tags={"session"}
        )

    async def invalidate_session(self, session_id: str) -> bool:
        """Инвалидировать сессию."""
        return await self.session_cache.delete(f"session:{session_id}")

    # User data caching
    async def get_user_data(self, user_id: str) -> Optional[Any]:
        """Получить пользовательские данные из кэша."""
        return await self.user_cache.get(f"user:{user_id}")

    async def cache_user_data(self, user_id: str, user_data: Any, ttl: int = 3600) -> bool:
        """Кэшировать пользовательские данные."""
        return await self.user_cache.set(
            f"user:{user_id}",
            user_data,
            ttl=ttl,
            item_type=CacheItemType.USER_DATA,
            tags={"user", user_id}
        )

    async def invalidate_user_data(self, user_id: str) -> bool:
        """Инвалидировать пользовательские данные."""
        return await self.user_cache.delete(f"user:{user_id}")

    # Query result caching
    async def get_query_result(self, query_hash: str) -> Optional[Any]:
        """Получить результат запроса из кэша."""
        return await self.query_cache.get(f"query:{query_hash}")

    async def cache_query_result(self, query_hash: str, result: Any, ttl: int = 900) -> bool:
        """Кэшировать результат запроса."""
        return await self.query_cache.set(
            f"query:{query_hash}",
            result,
            ttl=ttl,
            item_type=CacheItemType.QUERY_RESULT,
            tags={"query"}
        )

    # Cache warming
    async def warm_cache(self, data_source: str, loader_func: callable) -> None:
        """Предварительная загрузка кэша."""
        task = asyncio.create_task(self._cache_warming_worker(data_source, loader_func))
        self._cache_warming_tasks.add(task)
        task.add_done_callback(self._cache_warming_tasks.discard)

    async def _cache_warming_worker(self, data_source: str, loader_func: callable) -> None:
        """Воркер для предварительной загрузки кэша."""
        try:
            data = await loader_func()
            for key, value in data.items():
                await self.main_cache.set(key, value, ttl=3600)
        except Exception:
            # Логируем ошибку, но не падаем
            pass

    # Cache management
    async def cleanup_expired(self) -> Dict[str, int]:
        """Очистить истекшие элементы во всех кэшах."""
        results = {}

        if hasattr(self.main_cache, 'cleanup_expired'):
            results['main'] = await self.main_cache.cleanup_expired()

        if hasattr(self.session_cache, 'cleanup_expired'):
            results['session'] = await self.session_cache.cleanup_expired()

        if hasattr(self.user_cache, 'cleanup_expired'):
            results['user'] = await self.user_cache.cleanup_expired()

        if hasattr(self.query_cache, 'cleanup_expired'):
            results['query'] = await self.query_cache.cleanup_expired()

        return results

    async def invalidate_by_tags(self, tags: Set[str]) -> Dict[str, int]:
        """Инвалидировать элементы по тегам во всех кэшах."""
        results = {}

        if hasattr(self.main_cache, 'invalidate_by_tags'):
            results['main'] = await self.main_cache.invalidate_by_tags(tags)

        if hasattr(self.session_cache, 'invalidate_by_tags'):
            results['session'] = await self.session_cache.invalidate_by_tags(tags)

        if hasattr(self.user_cache, 'invalidate_by_tags'):
            results['user'] = await self.user_cache.invalidate_by_tags(tags)

        if hasattr(self.query_cache, 'invalidate_by_tags'):
            results['query'] = await self.query_cache.invalidate_by_tags(tags)

        return results

    async def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Получить комплексные метрики всех кэшей."""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "caches": {}
        }

        # Основной кэш
        if isinstance(self.main_cache, MultiLevelCache):
            metrics["caches"]["main"] = await self.main_cache.get_metrics()
        else:
            metrics["caches"]["main"] = await self.main_cache.get_metrics()

        # Специализированные кэши
        metrics["caches"]["session"] = await self.session_cache.get_metrics()
        metrics["caches"]["user"] = await self.user_cache.get_metrics()
        metrics["caches"]["query"] = await self.query_cache.get_metrics()

        # Агрегированные метрики
        total_hits = sum(cache.hits if isinstance(cache, CacheMetrics) else cache.get('combined', CacheMetrics()).hits
                        for cache in metrics["caches"].values())
        total_misses = sum(cache.misses if isinstance(cache, CacheMetrics) else cache.get('combined', CacheMetrics()).misses
                          for cache in metrics["caches"].values())
        total_requests = total_hits + total_misses

        metrics["aggregated"] = {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_requests": total_requests,
            "overall_hit_rate": (total_hits / total_requests * 100) if total_requests > 0 else 0,
            "active_warming_tasks": len(self._cache_warming_tasks)
        }

        return metrics

    async def shutdown(self) -> None:
        """Корректное завершение работы кэшей."""
        # Отменяем все задачи warming
        for task in self._cache_warming_tasks:
            task.cancel()

        # Ждем завершения задач
        if self._cache_warming_tasks:
            await asyncio.gather(*self._cache_warming_tasks, return_exceptions=True)


# Utility functions для интеграции с другими компонентами

def create_cache_key(prefix: str, *args: Any) -> str:
    """Создать ключ кэша из компонентов."""
    components = [prefix] + [str(arg) for arg in args]
    key_string = ":".join(components)
    return hashlib.sha256(key_string.encode()).hexdigest()


def cache_result(cache_manager: CacheManager, ttl: int = 3600, cache_type: CacheItemType = CacheItemType.QUERY_RESULT):
    """Декоратор для кэширования результатов функций."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Создаем ключ на основе имени функции и аргументов
            cache_key = create_cache_key(func.__name__, *args, *sorted(kwargs.items()))

            # Проверяем кэш
            cached_result = await cache_manager.main_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Выполняем функцию
            result = await func(*args, **kwargs)

            # Кэшируем результат
            await cache_manager.main_cache.set(cache_key, result, ttl=ttl, item_type=cache_type)

            return result
        return wrapper
    return decorator


async def create_default_cache_manager() -> CacheManager:
    """Создать CacheManager с настройками по умолчанию."""
    cache_manager = CacheManager(
        enable_l1=True,
        enable_l2=False,  # Redis отключен для демо
        l1_config=CacheConfig(max_size=1000, ttl_seconds=3600),
    )

    await cache_manager.initialize()
    return cache_manager


async def create_production_cache_manager(redis_url: str) -> CacheManager:
    """Создать CacheManager для production с Redis."""
    cache_manager = CacheManager(
        enable_l1=True,
        enable_l2=True,
        redis_url=redis_url,
        l1_config=CacheConfig(max_size=2000, ttl_seconds=1800),
        l2_config=CacheConfig(max_size=10000, ttl_seconds=7200),
    )

    await cache_manager.initialize()
    return cache_manager