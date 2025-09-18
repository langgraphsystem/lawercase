"""
Демонстрация CaseAgent functionality.

Показывает основные возможности CaseAgent:
- Создание дел
- CRUD операции
- Поиск и фильтрация
- Интеграция с workflow
"""

from __future__ import annotations

import asyncio
import uuid

from core.memory.memory_manager import MemoryManager
from core.groupagents.case_agent import CaseAgent
from core.groupagents.models import CaseType, CasePriority, CaseQuery
from core.orchestration.workflow_graph import WorkflowState, build_case_workflow
from core.orchestration.pipeline_manager import run


async def demo_case_operations():
    """Демонстрация основных операций CaseAgent"""
    print("🚀 === CaseAgent Demo ===\n")

    # Инициализация
    memory = MemoryManager()
    case_agent = CaseAgent(memory_manager=memory)

    user_id = "demo-user-001"

    print("1. 📝 Создание нового дела...")

    # Создание дела
    case_data = {
        "title": "Immigration Case - John Doe",
        "description": "H-1B visa extension application for software engineer",
        "case_type": CaseType.IMMIGRATION,
        "priority": CasePriority.HIGH,
        "client_id": "client-123",
        "assigned_lawyer": "lawyer-456",
        "tags": ["h1b", "visa", "extension", "software-engineer"]
    }

    case_record = await case_agent.acreate_case(
        user_id=user_id,
        case_data=case_data
    )

    print(f"✅ Дело создано: {case_record.case_id}")
    print(f"   Название: {case_record.title}")
    print(f"   Тип: {case_record.case_type}")
    print(f"   Статус: {case_record.status}")
    print(f"   Приоритет: {case_record.priority}\n")

    print("2. 📖 Получение дела...")

    # Получение дела
    retrieved_case = await case_agent.aget_case(case_record.case_id, user_id)
    print(f"✅ Дело получено: {retrieved_case.title}")
    print(f"   Описание: {retrieved_case.description}\n")

    print("3. ✏️ Обновление дела...")

    # Обновление дела
    updates = {
        "status": "active",
        "description": "H-1B visa extension application for senior software engineer - priority case",
        "change_reason": "Updated job title and priority status"
    }

    updated_case = await case_agent.aupdate_case(
        case_id=case_record.case_id,
        updates=updates,
        user_id=user_id
    )

    print(f"✅ Дело обновлено (версия {updated_case.version})")
    print(f"   Новый статус: {updated_case.status}")
    print(f"   Обновленное описание: {updated_case.description}\n")

    print("4. 🔍 Создание второго дела для демонстрации поиска...")

    # Создание второго дела
    case_data_2 = {
        "title": "Corporate Law - Startup Incorporation",
        "description": "Incorporation documents for tech startup",
        "case_type": CaseType.CORPORATE,
        "priority": CasePriority.MEDIUM,
        "client_id": "client-789",
        "assigned_lawyer": "lawyer-456",
        "tags": ["incorporation", "startup", "tech", "documents"]
    }

    case_record_2 = await case_agent.acreate_case(
        user_id=user_id,
        case_data=case_data_2
    )

    print(f"✅ Второе дело создано: {case_record_2.case_id}")
    print(f"   Название: {case_record_2.title}\n")

    print("5. 🔎 Поиск дел...")

    # Поиск всех дел
    search_query = CaseQuery(limit=10)
    all_cases = await case_agent.asearch_cases(search_query, user_id)

    print(f"✅ Найдено дел: {len(all_cases)}")
    for case in all_cases:
        print(f"   - {case.title} ({case.case_type}, {case.status})")
    print()

    # Поиск по типу
    print("6. 🎯 Поиск по типу дела (IMMIGRATION)...")

    immigration_query = CaseQuery(case_type=CaseType.IMMIGRATION)
    immigration_cases = await case_agent.asearch_cases(immigration_query, user_id)

    print(f"✅ Найдено иммиграционных дел: {len(immigration_cases)}")
    for case in immigration_cases:
        print(f"   - {case.title}")
    print()

    # Поиск по тексту
    print("7. 📝 Текстовый поиск (H-1B)...")

    text_query = CaseQuery(query="H-1B")
    h1b_cases = await case_agent.asearch_cases(text_query, user_id)

    print(f"✅ Найдено дел с 'H-1B': {len(h1b_cases)}")
    for case in h1b_cases:
        print(f"   - {case.title}")
    print()

    print("8. 📋 Просмотр версий дела...")

    # Получение версий
    versions = await case_agent.aget_case_versions(case_record.case_id)
    print(f"✅ Версий дела: {len(versions)}")
    for version in versions:
        print(f"   - Версия {version.version_number}: {version.change_reason}")
        print(f"     Изменено: {version.changed_at}")
    print()

    return case_record.case_id


async def demo_workflow_integration():
    """Демонстрация интеграции CaseAgent с workflow"""
    print("🔄 === Workflow Integration Demo ===\n")

    memory = MemoryManager()
    graph = build_case_workflow(memory)
    compiled_graph = graph.compile()

    user_id = "demo-user-002"
    thread_id = str(uuid.uuid4())

    print("1. 🚀 Создание дела через workflow...")

    # Создание дела через workflow
    initial_state = WorkflowState(
        thread_id=thread_id,
        user_id=user_id,
        case_operation="create",
        case_data={
            "title": "Family Law - Divorce Case",
            "description": "Divorce proceedings with child custody considerations",
            "case_type": CaseType.FAMILY,
            "priority": CasePriority.HIGH,
            "client_id": "client-family-001",
            "tags": ["divorce", "custody", "family"]
        }
    )

    # Запуск workflow
    final_state = await run(compiled_graph, initial_state, thread_id=thread_id)

    print("✅ Workflow завершен")

    # final_state - это словарь с именами узлов как ключами
    # Извлекаем state из узла update_rmt (финальный узел)
    if isinstance(final_state, dict) and 'update_rmt' in final_state:
        actual_state = final_state['update_rmt']
    else:
        actual_state = final_state

    # Проверяем тип состояния
    if isinstance(actual_state, dict):
        case_id = actual_state.get('case_id', 'unknown')
        case_result = actual_state.get('case_result', {})
        rmt_slots = actual_state.get('rmt_slots', {})
    else:
        case_id = getattr(actual_state, 'case_id', 'unknown')
        case_result = getattr(actual_state, 'case_result', {}) or {}
        rmt_slots = getattr(actual_state, 'rmt_slots', {}) or {}

    print(f"   Case ID: {case_id}")
    print(f"   Результат: {case_result.get('operation', 'unknown') if case_result else 'none'}")
    print(f"   RMT slots: {list(rmt_slots.keys()) if rmt_slots else []}")

    if case_result and 'case' in case_result:
        case = case_result['case']
        print(f"   Название дела: {case['title']}")
    print()

    print("2. 🔍 Получение дела через workflow...")

    # Получение дела через workflow
    get_state = WorkflowState(
        thread_id=str(uuid.uuid4()),
        user_id=user_id,
        case_operation="get",
        case_id=case_id
    )

    get_final_state = await run(compiled_graph, get_state)

    # Обработка результата workflow
    if isinstance(get_final_state, dict) and 'update_rmt' in get_final_state:
        get_actual_state = get_final_state['update_rmt']
    else:
        get_actual_state = get_final_state

    # Проверяем тип состояния
    if isinstance(get_actual_state, dict):
        get_case_result = get_actual_state.get('case_result', {})
    else:
        get_case_result = getattr(get_actual_state, 'case_result', {}) or {}

    print("✅ Дело получено через workflow")
    if get_case_result and 'case' in get_case_result:
        case = get_case_result['case']
        print(f"   Название: {case['title']}")
        print(f"   Описание: {case['description']}")
        print(f"   Статус: {case['status']}")
    print()

    print("3. 🔎 Поиск дел через workflow...")

    # Поиск через workflow
    search_state = WorkflowState(
        thread_id=str(uuid.uuid4()),
        user_id=user_id,
        case_operation="search",
        case_data={
            "case_type": CaseType.FAMILY,
            "limit": 5
        }
    )

    search_final_state = await run(compiled_graph, search_state)

    # Обработка результата workflow
    if isinstance(search_final_state, dict) and 'update_rmt' in search_final_state:
        search_actual_state = search_final_state['update_rmt']
    else:
        search_actual_state = search_final_state

    # Проверяем тип состояния
    if isinstance(search_actual_state, dict):
        search_case_result = search_actual_state.get('case_result', {})
    else:
        search_case_result = getattr(search_actual_state, 'case_result', {}) or {}

    print("✅ Поиск завершен через workflow")
    if search_case_result:
        count = search_case_result.get('count', 0)
        print(f"   Найдено дел: {count}")

        cases = search_case_result.get('cases', [])
        for case in cases:
            print(f"   - {case['title']} ({case['case_type']})")
    print()

    return case_id


async def demo_error_handling():
    """Демонстрация обработки ошибок"""
    print("⚠️ === Error Handling Demo ===\n")

    memory = MemoryManager()
    case_agent = CaseAgent(memory_manager=memory)
    user_id = "demo-user-003"

    print("1. 🚫 Попытка получить несуществующее дело...")

    try:
        await case_agent.aget_case("non-existent-case-id", user_id)
    except Exception as e:
        print(f"✅ Ошибка корректно обработана: {type(e).__name__}")
        print(f"   Сообщение: {str(e)}")
    print()

    print("2. ❌ Попытка создать дело с некорректными данными...")

    try:
        invalid_case_data = {
            "title": "",  # Пустое название
            "description": "Short",  # Слишком короткое описание
            "case_type": CaseType.IMMIGRATION,
            "client_id": "",  # Пустой client_id
        }
        await case_agent.acreate_case(user_id, invalid_case_data)
    except Exception as e:
        print(f"✅ Валидация сработала: {type(e).__name__}")
        print(f"   Сообщение: {str(e)}")
    print()

    print("3. 🔒 Тест optimistic locking...")

    # Создание дела
    valid_case_data = {
        "title": "Test Case for Locking",
        "description": "This case will be used to test optimistic locking mechanism",
        "case_type": CaseType.CIVIL,
        "client_id": "client-test-001",
    }

    case_record = await case_agent.acreate_case(user_id, valid_case_data)
    print(f"✅ Тестовое дело создано: {case_record.case_id}")

    # Попытка обновить с неправильной версией
    try:
        await case_agent.aupdate_case(
            case_id=case_record.case_id,
            updates={"title": "Updated Title"},
            user_id=user_id,
            expected_version=999  # Неправильная версия
        )
    except Exception as e:
        print(f"✅ Optimistic locking сработал: {type(e).__name__}")
        print(f"   Сообщение: {str(e)}")
    print()


async def main():
    """Главная функция демонстрации"""
    print("🎯 MEGA AGENT PRO - CaseAgent Demonstration")
    print("=" * 50)
    print()

    try:
        # Основные операции
        case_id_1 = await demo_case_operations()

        # Интеграция с workflow
        case_id_2 = await demo_workflow_integration()

        # Обработка ошибок
        await demo_error_handling()

        print("🎉 === Demo Completed Successfully ===")
        print(f"Created cases: {case_id_1}, {case_id_2}")
        print("All CaseAgent functionality demonstrated!")

    except Exception as e:
        print(f"❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())