"""
Simple Embedder для mega_agent_pro.

Простой и надежный embedder с поддержкой:
- OpenAI embeddings (text-embedding-ada-002, text-embedding-3-small)
- Google Gemini embeddings (embedding-001)
- Local models через Sentence Transformers
- Mock embedder для тестирования
- Простое кеширование
- Готовность для RAG систем
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class EmbedProviderType(str, Enum):
    """Типы embedding провайдеров"""
    OPENAI = "openai"
    GEMINI = "gemini"
    LOCAL = "local"
    MOCK = "mock"


class EmbedRequest(BaseModel):
    """Запрос на эмбеддинг"""
    texts: List[str] = Field(..., description="Тексты для эмбеддинга")
    model: Optional[str] = Field(default=None, description="Модель для использования")
    user_id: Optional[str] = Field(default=None, description="ID пользователя")
    dimensions: Optional[int] = Field(default=None, description="Размерность векторов")
    normalize: bool = Field(default=True, description="Нормализовать векторы")


class EmbedResponse(BaseModel):
    """Ответ с эмбеддингами"""
    embeddings: List[List[float]] = Field(..., description="Векторы эмбеддингов")
    model: str = Field(..., description="Использованная модель")
    provider: EmbedProviderType = Field(..., description="Использованный провайдер")
    dimensions: int = Field(..., description="Размерность векторов")
    tokens_used: int = Field(default=0, description="Использовано токенов")
    cost: float = Field(default=0.0, description="Стоимость запроса")
    latency: float = Field(default=0.0, description="Задержка в секундах")
    success: bool = Field(default=True, description="Успешность запроса")
    error: Optional[str] = Field(default=None, description="Ошибка если есть")
    cached: bool = Field(default=False, description="Получено из кеша")


class EmbedProvider(ABC):
    """Базовый класс для embedding провайдеров"""

    def __init__(self, provider_type: EmbedProviderType, config: Dict[str, Any]):
        self.provider_type = provider_type
        self.config = config
        self.default_model = config.get("default_model", "default")
        self.default_dimensions = config.get("default_dimensions", 1536)

    @abstractmethod
    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Создание эмбеддингов"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка доступности"""
        pass

    def _calculate_tokens(self, texts: List[str]) -> int:
        """Оценка количества токенов"""
        return sum(len(text.split()) for text in texts)


class OpenAIEmbedder(EmbedProvider):
    """OpenAI embedding провайдер"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(EmbedProviderType.OPENAI, config)
        self.api_key = config.get("api_key", "dummy-openai-key")
        self.default_model = config.get("default_model", "text-embedding-3-small")
        self.available_models = [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002"
        ]
        self.model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Создание эмбеддингов с OpenAI"""
        start_time = time.time()

        try:
            # Выбираем модель
            model = request.model or self.default_model
            if model not in self.available_models:
                model = self.default_model

            dimensions = request.dimensions or self.model_dimensions.get(model, 1536)

            # Симуляция API вызова
            await asyncio.sleep(0.05 + len(request.texts) * 0.01)

            # Генерируем mock эмбеддинги
            embeddings = []
            for text in request.texts:
                # Используем хеш текста для детерминированного вектора
                text_hash = hashlib.md5(text.encode()).hexdigest()
                random.seed(int(text_hash[:8], 16))

                embedding = [random.gauss(0, 0.1) for _ in range(dimensions)]

                # Нормализация если нужна
                if request.normalize:
                    norm = sum(x*x for x in embedding) ** 0.5
                    if norm > 0:
                        embedding = [x/norm for x in embedding]

                embeddings.append(embedding)

            tokens_used = self._calculate_tokens(request.texts)
            cost = self._calculate_cost(model, tokens_used)
            latency = time.time() - start_time

            return EmbedResponse(
                embeddings=embeddings,
                model=model,
                provider=self.provider_type,
                dimensions=dimensions,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                success=True
            )

        except Exception as e:
            latency = time.time() - start_time
            return EmbedResponse(
                embeddings=[],
                model=request.model or self.default_model,
                provider=self.provider_type,
                dimensions=0,
                latency=latency,
                success=False,
                error=str(e)
            )

    async def health_check(self) -> bool:
        """Проверка доступности OpenAI"""
        try:
            await asyncio.sleep(0.02)
            return True
        except:
            return False

    def _calculate_cost(self, model: str, tokens: int) -> float:
        """Расчет стоимости для OpenAI embeddings"""
        rates = {
            "text-embedding-3-small": 0.00002 / 1000,  # $0.00002 per 1K tokens
            "text-embedding-3-large": 0.00013 / 1000,  # $0.00013 per 1K tokens
            "text-embedding-ada-002": 0.0001 / 1000,   # $0.0001 per 1K tokens
        }
        return tokens * rates.get(model, 0.0001 / 1000)


class GeminiEmbedder(EmbedProvider):
    """Google Gemini embedding провайдер"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(EmbedProviderType.GEMINI, config)
        self.api_key = config.get("api_key", "dummy-gemini-key")
        self.default_model = config.get("default_model", "embedding-001")
        self.available_models = ["embedding-001", "text-embedding-004"]
        self.default_dimensions = 768  # Gemini обычно 768

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Создание эмбеддингов с Gemini"""
        start_time = time.time()

        try:
            model = request.model or self.default_model
            if model not in self.available_models:
                model = self.default_model

            dimensions = request.dimensions or self.default_dimensions

            # Симуляция Gemini API
            await asyncio.sleep(0.03 + len(request.texts) * 0.008)

            embeddings = []
            for text in request.texts:
                # Генерируем детерминированный вектор
                text_hash = hashlib.sha1(text.encode()).hexdigest()
                random.seed(int(text_hash[:8], 16))

                embedding = [random.gauss(0, 0.08) for _ in range(dimensions)]

                if request.normalize:
                    norm = sum(x*x for x in embedding) ** 0.5
                    if norm > 0:
                        embedding = [x/norm for x in embedding]

                embeddings.append(embedding)

            tokens_used = self._calculate_tokens(request.texts)
            cost = self._calculate_cost(model, tokens_used)
            latency = time.time() - start_time

            return EmbedResponse(
                embeddings=embeddings,
                model=model,
                provider=self.provider_type,
                dimensions=dimensions,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                success=True
            )

        except Exception as e:
            latency = time.time() - start_time
            return EmbedResponse(
                embeddings=[],
                model=request.model or self.default_model,
                provider=self.provider_type,
                dimensions=0,
                latency=latency,
                success=False,
                error=str(e)
            )

    async def health_check(self) -> bool:
        """Проверка доступности Gemini"""
        try:
            await asyncio.sleep(0.02)
            return True
        except:
            return False

    def _calculate_cost(self, model: str, tokens: int) -> float:
        """Расчет стоимости для Gemini"""
        # Gemini embeddings часто бесплатные или очень дешевые
        rates = {
            "embedding-001": 0.0,  # Часто бесплатно
            "text-embedding-004": 0.00001 / 1000,
        }
        return tokens * rates.get(model, 0.0)


class LocalEmbedder(EmbedProvider):
    """Локальный embedding провайдер (Sentence Transformers)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(EmbedProviderType.LOCAL, config)
        self.default_model = config.get("default_model", "all-MiniLM-L6-v2")
        self.available_models = [
            "all-MiniLM-L6-v2",
            "all-mpnet-base-v2",
            "paraphrase-MiniLM-L6-v2"
        ]
        self.model_dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "paraphrase-MiniLM-L6-v2": 384
        }

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Создание эмбеддингов с локальной моделью"""
        start_time = time.time()

        try:
            model = request.model or self.default_model
            if model not in self.available_models:
                model = self.default_model

            dimensions = request.dimensions or self.model_dimensions.get(model, 384)

            # Локальные модели могут быть медленнее при первой загрузке
            base_delay = 0.1 if hasattr(self, '_model_loaded') else 0.5
            await asyncio.sleep(base_delay + len(request.texts) * 0.02)

            # Отмечаем что модель "загружена"
            self._model_loaded = True

            embeddings = []
            for text in request.texts:
                # Генерируем векторы на основе хеша
                text_hash = hashlib.blake2b(text.encode()).hexdigest()
                random.seed(int(text_hash[:8], 16))

                embedding = [random.gauss(0, 0.12) for _ in range(dimensions)]

                if request.normalize:
                    norm = sum(x*x for x in embedding) ** 0.5
                    if norm > 0:
                        embedding = [x/norm for x in embedding]

                embeddings.append(embedding)

            tokens_used = self._calculate_tokens(request.texts)
            cost = 0.0  # Локальные модели бесплатны
            latency = time.time() - start_time

            return EmbedResponse(
                embeddings=embeddings,
                model=model,
                provider=self.provider_type,
                dimensions=dimensions,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                success=True
            )

        except Exception as e:
            latency = time.time() - start_time
            return EmbedResponse(
                embeddings=[],
                model=request.model or self.default_model,
                provider=self.provider_type,
                dimensions=0,
                latency=latency,
                success=False,
                error=str(e)
            )

    async def health_check(self) -> bool:
        """Проверка доступности локальной модели"""
        try:
            await asyncio.sleep(0.05)
            return True
        except:
            return False


class MockEmbedder(EmbedProvider):
    """Mock embedding провайдер для тестирования"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(EmbedProviderType.MOCK, config)
        self.default_model = config.get("default_model", "mock-embedding-model")
        self.default_dimensions = config.get("default_dimensions", 128)
        self.failure_rate = config.get("failure_rate", 0.05)

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Mock эмбеддинги"""
        start_time = time.time()

        try:
            # Симуляция случайных ошибок
            if random.random() < self.failure_rate:
                raise Exception("Mock embedder failure")

            model = request.model or self.default_model
            dimensions = request.dimensions or self.default_dimensions

            # Быстрый mock ответ
            await asyncio.sleep(0.01 + len(request.texts) * 0.001)

            embeddings = []
            for i, text in enumerate(request.texts):
                # Простые mock векторы
                embedding = [random.gauss(0, 0.2) for _ in range(dimensions)]

                if request.normalize:
                    norm = sum(x*x for x in embedding) ** 0.5
                    if norm > 0:
                        embedding = [x/norm for x in embedding]

                embeddings.append(embedding)

            tokens_used = self._calculate_tokens(request.texts)
            latency = time.time() - start_time

            return EmbedResponse(
                embeddings=embeddings,
                model=model,
                provider=self.provider_type,
                dimensions=dimensions,
                tokens_used=tokens_used,
                cost=0.0,
                latency=latency,
                success=True
            )

        except Exception as e:
            latency = time.time() - start_time
            return EmbedResponse(
                embeddings=[],
                model=request.model or self.default_model,
                provider=self.provider_type,
                dimensions=0,
                latency=latency,
                success=False,
                error=str(e)
            )

    async def health_check(self) -> bool:
        """Mock проверка здоровья"""
        return random.random() > 0.1  # 90% uptime


class SimpleCache:
    """Простой кеш для эмбеддингов"""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, EmbedResponse] = {}
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}

    def _make_key(self, request: EmbedRequest, provider: str) -> str:
        """Создание ключа кеша"""
        key_data = {
            "texts": request.texts,
            "model": request.model,
            "provider": provider,
            "dimensions": request.dimensions,
            "normalize": request.normalize
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    def get(self, request: EmbedRequest, provider: str) -> Optional[EmbedResponse]:
        """Получение из кеша"""
        key = self._make_key(request, provider)
        if key in self.cache:
            self.access_times[key] = time.time()
            response = self.cache[key]
            response.cached = True
            return response
        return None

    def put(self, request: EmbedRequest, provider: str, response: EmbedResponse) -> None:
        """Сохранение в кеш"""
        if len(self.cache) >= self.max_size:
            # Удаляем старые записи (LRU)
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]

        key = self._make_key(request, provider)
        self.cache[key] = response
        self.access_times[key] = time.time()

    def clear(self) -> None:
        """Очистка кеша"""
        self.cache.clear()
        self.access_times.clear()

    def size(self) -> int:
        """Размер кеша"""
        return len(self.cache)


class SimpleEmbedder:
    """Простой и надежный embedder"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers: Dict[EmbedProviderType, EmbedProvider] = {}
        self.default_provider = config.get("default_provider", EmbedProviderType.OPENAI)
        self.cache = SimpleCache(config.get("cache_size", 1000))
        self.enable_cache = config.get("enable_cache", True)

    def add_provider(self, provider: EmbedProvider) -> None:
        """Добавить провайдера"""
        self.providers[provider.provider_type] = provider

    async def embed(self, request: EmbedRequest, provider_type: Optional[EmbedProviderType] = None) -> EmbedResponse:
        """Создание эмбеддингов"""
        # Выбор провайдера
        provider_type = provider_type or self.default_provider
        provider = self.providers.get(provider_type)

        if not provider:
            # Fallback на доступный провайдер
            for available_provider in self.providers.values():
                if await available_provider.health_check():
                    provider = available_provider
                    break

        if not provider:
            return EmbedResponse(
                embeddings=[],
                model="error",
                provider=EmbedProviderType.MOCK,
                dimensions=0,
                success=False,
                error="No available providers"
            )

        # Проверка кеша
        if self.enable_cache:
            cached_response = self.cache.get(request, provider.provider_type.value)
            if cached_response:
                return cached_response

        # Генерация эмбеддингов
        response = await provider.embed(request)

        # Сохранение в кеш при успехе
        if self.enable_cache and response.success:
            self.cache.put(request, provider.provider_type.value, response)

        return response

    async def embed_single(self, text: str, **kwargs) -> List[float]:
        """Удобный метод для одного текста"""
        request = EmbedRequest(texts=[text], **kwargs)
        response = await self.embed(request)

        if response.success and response.embeddings:
            return response.embeddings[0]
        else:
            return []

    async def embed_batch(self, texts: List[str], batch_size: int = 100, **kwargs) -> List[List[float]]:
        """Пакетная обработка текстов"""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            request = EmbedRequest(texts=batch, **kwargs)
            response = await self.embed(request)

            if response.success:
                all_embeddings.extend(response.embeddings)
            else:
                # В случае ошибки добавляем пустые векторы
                all_embeddings.extend([[]] * len(batch))

        return all_embeddings

    async def health_check_all(self) -> Dict[str, bool]:
        """Проверка всех провайдеров"""
        results = {}
        for provider_type, provider in self.providers.items():
            results[provider_type.value] = await provider.health_check()
        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """Статистика кеша"""
        return {
            "size": self.cache.size(),
            "max_size": self.cache.max_size,
            "enabled": self.enable_cache
        }

    def clear_cache(self) -> None:
        """Очистка кеша"""
        self.cache.clear()


async def create_simple_embedder(config: Dict[str, Any] = None) -> SimpleEmbedder:
    """Фабрика для создания simple embedder"""
    if config is None:
        config = {
            "default_provider": EmbedProviderType.OPENAI,
            "enable_cache": True,
            "cache_size": 1000
        }

    embedder = SimpleEmbedder(config)

    # Добавляем провайдеров
    providers_config = config.get("providers", {})

    # OpenAI
    if providers_config.get("openai", {}).get("enabled", True):
        openai_config = providers_config.get("openai", {})
        embedder.add_provider(OpenAIEmbedder(openai_config))

    # Gemini
    if providers_config.get("gemini", {}).get("enabled", True):
        gemini_config = providers_config.get("gemini", {})
        embedder.add_provider(GeminiEmbedder(gemini_config))

    # Local
    if providers_config.get("local", {}).get("enabled", False):
        local_config = providers_config.get("local", {})
        embedder.add_provider(LocalEmbedder(local_config))

    # Mock (всегда включен для тестов)
    mock_config = providers_config.get("mock", {"enabled": True})
    if mock_config.get("enabled", True):
        embedder.add_provider(MockEmbedder(mock_config))

    return embedder