#!/usr/bin/env python3
"""
Тест всех LLM провайдеров
"""

import asyncio
from core.llm_router import create_llm_router, LLMRequest, ModelType

async def test_all_providers():
    """Тест всех доступных провайдеров"""
    print("🚀 ТЕСТ ВСЕХ LLM ПРОВАЙДЕРОВ")
    print("=" * 50)

    # Конфигурация со всеми провайдерами
    config = {
        "providers": {
            "openai": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "claude": {"enabled": True, "api_key": "demo-key"},
            "mock": {"enabled": True, "failure_rate": 0.05}
        }
    }

    router = await create_llm_router(config)

    # Тестируем каждый провайдер отдельно
    providers_to_test = ["openai", "gemini", "claude", "mock"]

    for provider_name in providers_to_test:
        print(f"\n🤖 === Тестирование {provider_name.upper()} ===")

        request = LLMRequest(
            messages=[{"role": "user", "content": f"Привет! Скажи что ты {provider_name}"}],
            model_type=ModelType.CHAT,
            max_tokens=100,
            provider_preference=[provider_name]  # Принудительно выбираем конкретный провайдер
        )

        response = await router.route_request(request)

        print(f"   Выбранный провайдер: {response.provider.value}")
        print(f"   Модель: {response.model}")
        print(f"   Успех: {'✅' if response.success else '❌'}")
        print(f"   Ответ: {response.content}")
        print(f"   Токены: {response.tokens_used}")
        print(f"   Время: {response.latency:.3f}s")
        print(f"   Стоимость: ${response.cost:.6f}")

    # Тест автоматического выбора провайдера
    print(f"\n🎯 === Автоматический выбор провайдера ===")
    auto_request = LLMRequest(
        messages=[{"role": "user", "content": "Напиши краткий юридический совет"}],
        model_type=ModelType.CHAT,
        max_tokens=100
    )

    auto_response = await router.route_request(auto_request)
    print(f"   Автоматически выбран: {auto_response.provider.value}")
    print(f"   Модель: {auto_response.model}")
    print(f"   Ответ: {auto_response.content}")

    # Финальная статистика
    print(f"\n📊 === Финальная статистика ===")
    stats = await router.get_providers_stats()
    for provider_name, provider_stats in stats.items():
        print(f"   {provider_name}:")
        print(f"     Запросов: {provider_stats.total_requests}")
        print(f"     Успешность: {provider_stats.success_rate:.1%}")
        print(f"     Средняя задержка: {provider_stats.average_latency:.3f}s")
        print(f"     Общая стоимость: ${provider_stats.total_cost:.6f}")

if __name__ == "__main__":
    asyncio.run(test_all_providers())