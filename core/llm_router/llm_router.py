"""
Advanced LLM Router для mega_agent_pro.

Intelligent routing system for managing multiple LLM providers with:
- Provider selection based on task requirements
- Load balancing и failover mechanisms
- Cost optimization и quota management
- Performance monitoring и analytics
- Rate limiting и circuit breaker patterns
- Mock providers for development и testing
"""

from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Типы LLM провайдеров"""
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    LOCAL = "local"
    MOCK = "mock"


class ModelType(str, Enum):
    """Типы моделей"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    VISION = "vision"
    CODE = "code"


class Priority(str, Enum):
    """Приоритеты запросов"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class LLMRequest(BaseModel):
    """Запрос к LLM"""
    messages: List[Dict[str, str]] = Field(..., description="Сообщения для обработки")
    model_type: ModelType = Field(default=ModelType.CHAT, description="Тип модели")
    max_tokens: int = Field(default=1000, description="Максимум токенов")
    temperature: float = Field(default=0.7, description="Температура генерации")
    priority: Priority = Field(default=Priority.NORMAL, description="Приоритет запроса")
    provider_preference: Optional[List[str]] = Field(default=None, description="Предпочтительные провайдеры")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Контекст запроса")
    user_id: Optional[str] = Field(default=None, description="ID пользователя")
    session_id: Optional[str] = Field(default=None, description="ID сессии")


class LLMResponse(BaseModel):
    """Ответ от LLM"""
    content: str = Field(..., description="Содержание ответа")
    provider: ProviderType = Field(..., description="Использованный провайдер")
    model: str = Field(..., description="Использованная модель")
    tokens_used: int = Field(default=0, description="Использовано токенов")
    cost: float = Field(default=0.0, description="Стоимость запроса")
    latency: float = Field(default=0.0, description="Задержка в секундах")
    success: bool = Field(default=True, description="Успешность запроса")
    error: Optional[str] = Field(default=None, description="Ошибка если есть")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные данные")


class ProviderStats(BaseModel):
    """Статистика провайдера"""
    total_requests: int = Field(default=0, description="Всего запросов")
    successful_requests: int = Field(default=0, description="Успешных запросов")
    failed_requests: int = Field(default=0, description="Неудачных запросов")
    total_tokens: int = Field(default=0, description="Всего токенов")
    total_cost: float = Field(default=0.0, description="Общая стоимость")
    average_latency: float = Field(default=0.0, description="Средняя задержка")
    last_request: Optional[datetime] = Field(default=None, description="Последний запрос")
    success_rate: float = Field(default=0.0, description="Процент успеха")
    is_available: bool = Field(default=True, description="Доступность")


class LLMProvider(ABC):
    """Базовый класс для LLM провайдеров"""

    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        self.provider_type = provider_type
        self.config = config
        self.stats = ProviderStats()
        self.rate_limiter = RateLimiter(
            requests_per_minute=config.get("rate_limit", 60),
            tokens_per_minute=config.get("token_limit", 60000)
        )

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Генерация ответа"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка доступности провайдера"""
        pass

    def update_stats(self, response: LLMResponse) -> None:
        """Обновление статистики"""
        self.stats.total_requests += 1
        self.stats.last_request = datetime.utcnow()

        if response.success:
            self.stats.successful_requests += 1
            self.stats.total_tokens += response.tokens_used
            self.stats.total_cost += response.cost

            # Обновляем среднюю задержку
            if self.stats.average_latency == 0:
                self.stats.average_latency = response.latency
            else:
                self.stats.average_latency = (
                    self.stats.average_latency * 0.9 + response.latency * 0.1
                )
        else:
            self.stats.failed_requests += 1

        # Обновляем процент успеха
        if self.stats.total_requests > 0:
            self.stats.success_rate = (
                self.stats.successful_requests / self.stats.total_requests * 100
            )


class RateLimiter:
    """Ограничитель скорости запросов"""

    def __init__(self, requests_per_minute: int, tokens_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.requests_history: List[datetime] = []
        self.tokens_history: List[tuple[datetime, int]] = []

    async def check_and_wait(self, tokens_needed: int) -> bool:
        """Проверка лимитов и ожидание если нужно"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Очистка старых записей
        self.requests_history = [t for t in self.requests_history if t > minute_ago]
        self.tokens_history = [(t, tokens) for t, tokens in self.tokens_history if t > minute_ago]

        # Проверка лимита запросов
        if len(self.requests_history) >= self.requests_per_minute:
            wait_time = 60 - (now - self.requests_history[0]).total_seconds()
            await asyncio.sleep(max(0, wait_time))

        # Проверка лимита токенов
        current_tokens = sum(tokens for _, tokens in self.tokens_history)
        if current_tokens + tokens_needed > self.tokens_per_minute:
            wait_time = 60 - (now - self.tokens_history[0][0]).total_seconds()
            await asyncio.sleep(max(0, wait_time))

        # Записываем использование
        self.requests_history.append(now)
        self.tokens_history.append((now, tokens_needed))

        return True


class OpenAIProvider(LLMProvider):
    """OpenAI провайдер"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.OPENAI, config)
        self.api_key = config.get("api_key", "dummy-key")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.models = {
            ModelType.CHAT: ["gpt-5", "gpt-4", "gpt-3.5-turbo"],
            ModelType.CODE: ["gpt-5", "gpt-4", "gpt-3.5-turbo"],
            ModelType.VISION: ["gpt-5", "gpt-4-vision-preview"]
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Генерация с OpenAI"""
        start_time = time.time()

        try:
            # Ограничение скорости
            await self.rate_limiter.check_and_wait(request.max_tokens)

            # Выбираем модель
            available_models = self.models.get(request.model_type, ["gpt-3.5-turbo"])
            model = available_models[0]

            # Note: GPT-5 introduces a new Responses API and parameters like `reasoning_effort`.
            # This simulation does not include these new features.
            # Симуляция API вызова (в реальности здесь был бы HTTP запрос)
            await asyncio.sleep(0.1 + random.uniform(0, 0.5))  # Симуляция сетевой задержки

            # Генерируем ответ
            if request.model_type == ModelType.CHAT:
                content = f"OpenAI {model} response to: {request.messages[-1].get('content', 'empty')[:50]}..."
            else:
                content = f"OpenAI {model} generated content for {request.model_type}"

            tokens_used = len(content) // 4  # Примерная оценка токенов
            cost = self._calculate_cost(model, tokens_used)
            latency = time.time() - start_time

            response = LLMResponse(
                content=content,
                provider=self.provider_type,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                success=True,
                metadata={"api_version": "v1", "endpoint": self.base_url}
            )

            self.update_stats(response)
            return response

        except Exception as e:
            latency = time.time() - start_time
            response = LLMResponse(
                content="",
                provider=self.provider_type,
                model="unknown",
                latency=latency,
                success=False,
                error=str(e)
            )
            self.update_stats(response)
            return response

    async def health_check(self) -> bool:
        """Проверка здоровья OpenAI"""
        try:
            # Симуляция проверки API
            await asyncio.sleep(0.1)
            return True
        except:
            return False

    def _calculate_cost(self, model: str, tokens: int) -> float:
        """Расчет стоимости"""
        rates = {
            "gpt-5": 0.05 / 1000,  # Placeholder cost
            "gpt-4": 0.03 / 1000,
            "gpt-3.5-turbo": 0.002 / 1000,
        }
        return tokens * rates.get(model, 0.002 / 1000)


class GeminiProvider(LLMProvider):
    """Google Gemini провайдер"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.GEMINI, config)
        self.api_key = config.get("api_key", "dummy-key")
        self.models = {
            ModelType.CHAT: ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-pro"],
            ModelType.VISION: ["gemini-2.5-pro", "gemini-pro-vision"]
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Генерация с Gemini"""
        start_time = time.time()

        try:
            await self.rate_limiter.check_and_wait(request.max_tokens)

            available_models = self.models.get(request.model_type, ["gemini-pro"])
            model = available_models[0]

            # Симуляция API вызова
            await asyncio.sleep(0.05 + random.uniform(0, 0.3))

            if request.model_type == ModelType.CHAT:
                content = f"Gemini {model} response to: {request.messages[-1].get('content', 'empty')[:50]}..."
            else:
                content = f"Gemini {model} generated content for {request.model_type}"

            tokens_used = len(content) // 4
            cost = self._calculate_cost(model, tokens_used)
            latency = time.time() - start_time

            response = LLMResponse(
                content=content,
                provider=self.provider_type,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                success=True,
                metadata={"api_version": "v1beta", "model_version": "001"}
            )

            self.update_stats(response)
            return response

        except Exception as e:
            latency = time.time() - start_time
            response = LLMResponse(
                content="",
                provider=self.provider_type,
                model="unknown",
                latency=latency,
                success=False,
                error=str(e)
            )
            self.update_stats(response)
            return response

    async def health_check(self) -> bool:
        """Проверка здоровья Gemini"""
        try:
            await asyncio.sleep(0.05)
            return True
        except:
            return False

    def _calculate_cost(self, model: str, tokens: int) -> float:
        """Расчет стоимости для Gemini"""
        rates = {
            "gemini-2.5-pro": 0.003 / 1000,  # Placeholder cost
            "gemini-2.0-flash": 0.0015 / 1000,  # Placeholder cost
            "gemini-pro": 0.001 / 1000,
            "gemini-pro-vision": 0.002 / 1000,
        }
        return tokens * rates.get(model, 0.001 / 1000)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude провайдер"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.CLAUDE, config)
        self.api_key = config.get("api_key", "dummy-key")
        self.models = {
            ModelType.CHAT: ["claude-4-opus", "claude-4-sonnet", "claude-3-sonnet"],
            ModelType.CODE: ["claude-4-opus", "claude-3-sonnet"]
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Генерация с Claude"""
        start_time = time.time()

        try:
            await self.rate_limiter.check_and_wait(request.max_tokens)

            available_models = self.models.get(request.model_type, ["claude-3-haiku"])
            model = available_models[0]

            await asyncio.sleep(0.08 + random.uniform(0, 0.4))

            if request.model_type == ModelType.CHAT:
                content = f"Claude {model} response to: {request.messages[-1].get('content', 'empty')[:50]}..."
            else:
                content = f"Claude {model} generated content for {request.model_type}"

            tokens_used = len(content) // 4
            cost = self._calculate_cost(model, tokens_used)
            latency = time.time() - start_time

            response = LLMResponse(
                content=content,
                provider=self.provider_type,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                success=True,
                metadata={"api_version": "2023-06-01"}
            )

            self.update_stats(response)
            return response

        except Exception as e:
            latency = time.time() - start_time
            response = LLMResponse(
                content="",
                provider=self.provider_type,
                model="unknown",
                latency=latency,
                success=False,
                error=str(e)
            )
            self.update_stats(response)
            return response

    async def health_check(self) -> bool:
        """Проверка здоровья Claude"""
        try:
            await asyncio.sleep(0.08)
            return True
        except:
            return False

    def _calculate_cost(self, model: str, tokens: int) -> float:
        """Расчет стоимости для Claude"""
        rates = {
            "claude-4-opus": 0.025 / 1000,  # Placeholder cost
            "claude-4-sonnet": 0.018 / 1000,  # Placeholder cost
            "claude-3-sonnet": 0.015 / 1000,
            "claude-3-haiku": 0.0008 / 1000,
        }
        return tokens * rates.get(model, 0.015 / 1000)


class LocalProvider(LLMProvider):
    """Локальный провайдер (Ollama/HuggingFace)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.LOCAL, config)
        self.endpoint = config.get("endpoint", "http://localhost:11434")
        self.models = {
            ModelType.CHAT: ["llama2", "mistral", "codellama"],
            ModelType.CODE: ["codellama", "deepseek-coder"]
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Генерация с локальной моделью"""
        start_time = time.time()

        try:
            available_models = self.models.get(request.model_type, ["llama2"])
            model = available_models[0]

            # Локальные модели могут быть медленнее
            await asyncio.sleep(0.2 + random.uniform(0, 1.0))

            if request.model_type == ModelType.CHAT:
                content = f"Local {model} response to: {request.messages[-1].get('content', 'empty')[:50]}..."
            else:
                content = f"Local {model} generated content for {request.model_type}"

            tokens_used = len(content) // 4
            cost = 0.0  # Локальные модели бесплатные
            latency = time.time() - start_time

            response = LLMResponse(
                content=content,
                provider=self.provider_type,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                success=True,
                metadata={"endpoint": self.endpoint, "local": True}
            )

            self.update_stats(response)
            return response

        except Exception as e:
            latency = time.time() - start_time
            response = LLMResponse(
                content="",
                provider=self.provider_type,
                model="unknown",
                latency=latency,
                success=False,
                error=str(e)
            )
            self.update_stats(response)
            return response

    async def health_check(self) -> bool:
        """Проверка здоровья локального провайдера"""
        try:
            await asyncio.sleep(0.1)
            # В реальности проверяли бы доступность endpoint
            return True
        except:
            return False


class MockProvider(LLMProvider):
    """Mock провайдер для тестирования"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.MOCK, config)
        self.should_fail = config.get("should_fail", False)
        self.failure_rate = config.get("failure_rate", 0.1)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Mock генерация"""
        start_time = time.time()

        try:
            # Симуляция быстрого ответа
            await asyncio.sleep(0.01 + random.uniform(0, 0.05))

            # Симуляция ошибок
            if self.should_fail or random.random() < self.failure_rate:
                raise Exception("Mock provider failure")

            content = f"Mock response to: {request.messages[-1].get('content', 'empty')[:50]}..."
            tokens_used = len(content) // 4
            cost = 0.0
            latency = time.time() - start_time

            response = LLMResponse(
                content=content,
                provider=self.provider_type,
                model="mock-model",
                tokens_used=tokens_used,
                cost=cost,
                latency=latency,
                success=True,
                metadata={"mock": True}
            )

            self.update_stats(response)
            return response

        except Exception as e:
            latency = time.time() - start_time
            response = LLMResponse(
                content="",
                provider=self.provider_type,
                model="mock-model",
                latency=latency,
                success=False,
                error=str(e)
            )
            self.update_stats(response)
            return response

    async def health_check(self) -> bool:
        """Mock проверка здоровья"""
        return not self.should_fail


class LLMRouter:
    """Интеллектуальный роутер LLM запросов"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers: Dict[ProviderType, LLMProvider] = {}
        self.routing_rules = config.get("routing_rules", {})
        self.fallback_strategy = config.get("fallback_strategy", "round_robin")
        self.load_balancing = config.get("load_balancing", True)

    def add_provider(self, provider: LLMProvider) -> None:
        """Добавить провайдера"""
        self.providers[provider.provider_type] = provider

    async def route_request(self, request: LLMRequest) -> LLMResponse:
        """Маршрутизация запроса к подходящему провайдеру"""
        try:
            # 1. Выбор провайдера на основе правил
            selected_provider = await self._select_provider(request)

            if not selected_provider:
                # Если нет доступного провайдера, используем fallback
                selected_provider = await self._fallback_selection(request)

            if not selected_provider:
                return LLMResponse(
                    content="",
                    provider=ProviderType.MOCK,
                    model="error",
                    success=False,
                    error="No available providers"
                )

            # 2. Выполнение запроса
            response = await selected_provider.generate(request)

            # 3. Если запрос неудачен, пробуем fallback
            if not response.success and len(self.providers) > 1:
                fallback_provider = await self._get_fallback_provider(selected_provider.provider_type, request)
                if fallback_provider:
                    response = await fallback_provider.generate(request)

            return response

        except Exception as e:
            return LLMResponse(
                content="",
                provider=ProviderType.MOCK,
                model="error",
                success=False,
                error=f"Routing error: {str(e)}"
            )

    async def _select_provider(self, request: LLMRequest) -> Optional[LLMProvider]:
        """Выбор провайдера на основе правил"""

        # Приоритет: Явные предпочтения пользователя
        if request.provider_preference:
            for preferred_provider_str in request.provider_preference:
                try:
                    provider_type = ProviderType(preferred_provider_str)
                    provider = self.providers.get(provider_type)
                    if provider and provider.stats.is_available:
                        if await provider.health_check():
                            return provider
                except ValueError:
                    # Неизвестный тип провайдера, пропускаем
                    continue

        # Правило по приоритету
        if request.priority == Priority.CRITICAL:
            # Для критических запросов используем самый надежный провайдер
            return self._get_most_reliable_provider(request.model_type)

        # Правило по типу модели
        model_preferences = self.routing_rules.get("model_preferences", {})
        preferred_providers = model_preferences.get(request.model_type.value, [])

        for provider_type_str in preferred_providers:
            provider_type = ProviderType(provider_type_str)
            provider = self.providers.get(provider_type)
            if provider and provider.stats.is_available:
                if await provider.health_check():
                    return provider

        # Правило по стоимости (если указано в контексте)
        if request.context and request.context.get("optimize_cost", False):
            return self._get_cheapest_provider(request.model_type)

        # Правило по скорости
        if request.context and request.context.get("optimize_speed", False):
            return self._get_fastest_provider(request.model_type)

        # Загрузочная балансировка
        if self.load_balancing:
            return self._get_least_loaded_provider(request.model_type)

        return None

    async def _fallback_selection(self, request: LLMRequest) -> Optional[LLMProvider]:
        """Fallback выбор провайдера"""
        available_providers = []

        for provider in self.providers.values():
            if provider.stats.is_available and await provider.health_check():
                # Проверяем поддержку типа модели
                if hasattr(provider, 'models') and request.model_type in provider.models:
                    available_providers.append(provider)

        if not available_providers:
            return None

        if self.fallback_strategy == "round_robin":
            # Простая круговая балансировка
            provider_index = hash(request.user_id or "anonymous") % len(available_providers)
            return available_providers[provider_index]

        elif self.fallback_strategy == "least_loaded":
            return min(available_providers, key=lambda p: p.stats.total_requests)

        elif self.fallback_strategy == "fastest":
            return min(available_providers, key=lambda p: p.stats.average_latency or float('inf'))

        else:
            return available_providers[0]

    async def _get_fallback_provider(self, failed_provider: ProviderType, request: LLMRequest) -> Optional[LLMProvider]:
        """Получить fallback провайдера"""
        for provider_type, provider in self.providers.items():
            if (provider_type != failed_provider and
                provider.stats.is_available and
                await provider.health_check()):
                # Проверяем поддержку типа модели
                if hasattr(provider, 'models') and request.model_type in provider.models:
                    return provider
        return None

    def _get_most_reliable_provider(self, model_type: ModelType) -> Optional[LLMProvider]:
        """Самый надежный провайдер"""
        suitable_providers = [
            p for p in self.providers.values()
            if (p.stats.is_available and
                hasattr(p, 'models') and
                model_type in p.models)
        ]

        if not suitable_providers:
            return None

        return max(suitable_providers, key=lambda p: p.stats.success_rate)

    def _get_cheapest_provider(self, model_type: ModelType) -> Optional[LLMProvider]:
        """Самый дешевый провайдер"""
        # Локальные провайдеры обычно бесплатные
        for provider_type in [ProviderType.LOCAL, ProviderType.MOCK]:
            provider = self.providers.get(provider_type)
            if (provider and provider.stats.is_available and
                hasattr(provider, 'models') and model_type in provider.models):
                return provider

        # Иначе выбираем по средней стоимости
        suitable_providers = [
            p for p in self.providers.values()
            if (p.stats.is_available and
                hasattr(p, 'models') and
                model_type in p.models and
                p.stats.total_requests > 0)
        ]

        if suitable_providers:
            return min(suitable_providers, key=lambda p: p.stats.total_cost / p.stats.total_requests)

        return None

    def _get_fastest_provider(self, model_type: ModelType) -> Optional[LLMProvider]:
        """Самый быстрый провайдер"""
        suitable_providers = [
            p for p in self.providers.values()
            if (p.stats.is_available and
                hasattr(p, 'models') and
                model_type in p.models and
                p.stats.average_latency > 0)
        ]

        if suitable_providers:
            return min(suitable_providers, key=lambda p: p.stats.average_latency)

        return None

    def _get_least_loaded_provider(self, model_type: ModelType) -> Optional[LLMProvider]:
        """Наименее загруженный провайдер"""
        suitable_providers = [
            p for p in self.providers.values()
            if (p.stats.is_available and
                hasattr(p, 'models') and
                model_type in p.models)
        ]

        if suitable_providers:
            return min(suitable_providers, key=lambda p: p.stats.total_requests)

        return None

    async def get_providers_stats(self) -> Dict[str, ProviderStats]:
        """Получить статистику всех провайдеров"""
        stats = {}
        for provider_type, provider in self.providers.items():
            stats[provider_type.value] = provider.stats
        return stats

    async def health_check_all(self) -> Dict[str, bool]:
        """Проверка здоровья всех провайдеров"""
        results = {}
        for provider_type, provider in self.providers.items():
            results[provider_type.value] = await provider.health_check()
            provider.stats.is_available = results[provider_type.value]
        return results


async def create_llm_router(config: Dict[str, Any] = None) -> LLMRouter:
    """Фабрика для создания LLM роутера"""
    if config is None:
        config = {
            "routing_rules": {
                "model_preferences": {
                    "chat": ["openai", "gemini", "claude", "local"],
                    "code": ["openai", "claude", "local"],
                    "vision": ["openai", "gemini"]
                }
            },
            "fallback_strategy": "round_robin",
            "load_balancing": True
        }

    router = LLMRouter(config)

    # Добавляем провайдеров по умолчанию
    providers_config = config.get("providers", {})

    # OpenAI
    if providers_config.get("openai", {}).get("enabled", True):
        openai_config = providers_config.get("openai", {})
        router.add_provider(OpenAIProvider(openai_config))

    # Gemini
    if providers_config.get("gemini", {}).get("enabled", True):
        gemini_config = providers_config.get("gemini", {})
        router.add_provider(GeminiProvider(gemini_config))

    # Claude
    if providers_config.get("claude", {}).get("enabled", True):
        claude_config = providers_config.get("claude", {})
        router.add_provider(ClaudeProvider(claude_config))

    # Local
    if providers_config.get("local", {}).get("enabled", False):
        local_config = providers_config.get("local", {})
        router.add_provider(LocalProvider(local_config))

    # Mock (для тестирования)
    if providers_config.get("mock", {}).get("enabled", False):
        mock_config = providers_config.get("mock", {})
        router.add_provider(MockProvider(mock_config))

    return router