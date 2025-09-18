#!/usr/bin/env python3
"""
Тест для проверки доступности Claude в LLM Router
"""

import asyncio
from core.llm_router import create_llm_router, LLMRequest, ModelType

async def test_claude_availability():
    """Тест доступности Claude провайдера"""
    print("🔍 Проверка доступности Claude в LLM Router...")

    # Конфигурация с включенным Claude
    config = {
        "providers": {
            "openai": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "claude": {"enabled": True, "api_key": "demo-key"},
            "mock": {"enabled": True, "failure_rate": 0.05}
        }
    }

    # Создаем роутер
    router = await create_llm_router(config)

    # Проверяем список провайдеров
    print(f"\n📋 Загружено провайдеров: {len(router.providers)}")
    for provider_type, provider in router.providers.items():
        print(f"   ✅ {provider_type.value}: {provider.__class__.__name__}")

    # Проверяем health check всех провайдеров
    print("\n🏥 Health Check результаты:")
    health_results = await router.health_check_all()
    for provider_name, is_healthy in health_results.items():
        status = "✅ Healthy" if is_healthy else "❌ Unhealthy"
        print(f"   {provider_name}: {status}")

    # Тестируем запрос через Claude
    print("\n🧪 Тестирование Claude запроса...")

    request = LLMRequest(
        messages=[{"role": "user", "content": "Привет! Ты Claude?"}],
        model_type=ModelType.CHAT,
        max_tokens=100,
        provider_preference=["claude"]  # Принудительно выбираем Claude
    )

    response = await router.route_request(request)

    print(f"   Провайдер: {response.provider}")
    print(f"   Модель: {response.model}")
    print(f"   Успех: {response.success}")
    print(f"   Содержание: {response.content[:100]}...")
    print(f"   Токены: {response.tokens_used}")
    print(f"   Время: {response.latency:.3f}s")

    # Получаем статистику провайдеров
    print("\n📊 Статистика провайдеров:")
    stats = await router.get_providers_stats()
    for provider_name, provider_stats in stats.items():
        print(f"   {provider_name}:")
        print(f"     Доступен: {provider_stats.is_available}")
        print(f"     Запросов: {provider_stats.total_requests}")
        print(f"     Успешных: {provider_stats.successful_requests}")
        print(f"     Средняя задержка: {provider_stats.average_latency:.3f}s")

if __name__ == "__main__":
    asyncio.run(test_claude_availability())