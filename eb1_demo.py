"""
EB-1A Demo - Полный цикл обработки EB-1A петиции

Демонстрирует:
1. Создание петиции
2. Интерактивный опрос по 10 критериям USCIS
3. Оценку соответствия
4. Рекомендации

Запуск: python eb1_demo.py
"""

from __future__ import annotations

import asyncio

from core.groupagents.mega_agent import CommandType, MegaAgent, MegaAgentCommand, UserRole


async def run_eb1_demo():
    """Полный демо-сценарий EB-1A петиции"""

    print("=" * 80)
    print("🇺🇸 EB-1A PETITION DEMO - Employment-Based First Preference")
    print("=" * 80)
    print()

    # Инициализация MegaAgent
    print("📋 Инициализация системы...")
    agent = MegaAgent()
    user_id = "demo_user_001"
    user_role = UserRole.LAWYER

    print(f"✅ Пользователь: {user_id}")
    print(f"✅ Роль: {user_role.value}")
    print()

    # ========== ШАГ 1: СОЗДАНИЕ ПЕТИЦИИ ==========
    print("=" * 80)
    print("ШАГ 1: Создание новой EB-1A петиции")
    print("=" * 80)
    print()

    create_cmd = MegaAgentCommand(
        user_id=user_id, command_type=CommandType.EB1, action="create", payload={}
    )

    response = await agent.handle_command(create_cmd, user_role)

    if not response.success:
        print(f"❌ Ошибка: {response.error}")
        return

    result = response.result or {}
    petition_id = result.get("petition_id")
    welcome_message = result.get("message", "")

    print(welcome_message)
    print()
    print("-" * 80)
    print()

    # ========== ШАГ 2: ИНТЕРАКТИВНЫЙ ОПРОС ==========
    print("=" * 80)
    print("ШАГ 2: Интерактивный опрос (автоматические ответы)")
    print("=" * 80)
    print()

    # Симуляция ответов пользователя
    user_responses = [
        # Personal Info
        ("John Smith", "Ваше имя"),
        ("john.smith@example.com", "Email"),
        ("Russia", "Страна"),
        ("H-1B", "Визовый статус"),
        # Field of Expertise
        ("Artificial Intelligence", "Область"),
        ("15", "Лет опыта"),
        ("Lead AI Researcher", "Должность"),
        ("PhD in Computer Science", "Образование"),
        # Criterion 1: Awards
        ("да", "Награды"),
        ("Best Paper Award IEEE 2023\nGoogle AI Research Award 2022", "Список наград"),
        # Criterion 2: Membership
        ("да", "Членство в ассоциациях"),
        ("ACM Fellow - requires outstanding achievements\nIEEE Senior Member", "Ассоциации"),
        # Criterion 3: Press
        ("да", "Публикации в СМИ"),
        ("MIT Technology Review - AI Breakthrough\nWired Magazine - Top 10 AI Researchers", "СМИ"),
        # Criterion 4: Judging
        ("да", "Судейство"),
        ("NeurIPS reviewer 2020-2024\nACM SIGKDD Program Committee", "Судейство"),
        # Criterion 5: Contribution
        ("да", "Оригинальный вклад"),
        ("Developed new transformer architecture cited 5000+ times", "Вклад"),
        # Criterion 6: Scholarly
        ("да", "Научные публикации"),
        ("85", "Количество публикаций"),
        ("12500", "Цитирования"),
        # Criterion 7: Exhibition
        ("нет", "Выставки"),
        # Criterion 8: Leadership
        ("да", "Лидерство"),
        ("Director of AI Research at Google\nFounding member of OpenAI", "Лидерские роли"),
        # Criterion 9: Salary
        ("да", "Высокая зарплата"),
        ("450000", "Зарплата USD"),
        # Criterion 10: Commercial
        ("нет", "Коммерческий успех"),
    ]

    for i, (answer_text, question_hint) in enumerate(user_responses, 1):
        # Отправка ответа
        msg_cmd = MegaAgentCommand(
            user_id=user_id,
            command_type=CommandType.EB1,
            action="message",
            payload={"petition_id": petition_id, "message": answer_text},
        )

        response = await agent.handle_command(msg_cmd, user_role)

        if not response.success:
            print(f"❌ Ошибка на вопросе {i}: {response.error}")
            continue

        result = response.result or {}
        bot_response = result.get("bot_response", "")

        print(f"👤 [{question_hint}]: {answer_text}")
        print(f"🤖 Бот:\n{bot_response}")
        print()
        print("-" * 80)
        print()

        # Небольшая пауза для читаемости
        await asyncio.sleep(0.1)

        # Проверка на итоговую сводку
        if "ИТОГОВАЯ ОЦЕНКА" in bot_response:
            print("✅ Опросник завершен! Получена итоговая оценка.")
            print()
            break

    # ========== ШАГ 3: ПОЛУЧЕНИЕ СТАТУСА ==========
    print("=" * 80)
    print("ШАГ 3: Проверка статуса петиции")
    print("=" * 80)
    print()

    status_cmd = MegaAgentCommand(
        user_id=user_id,
        command_type=CommandType.EB1,
        action="status",
        payload={"petition_id": petition_id},
    )

    response = await agent.handle_command(status_cmd, user_role)

    if response.success:
        status = response.result or {}
        print(f"📋 Petition ID: {status.get('petition_id')}")
        print(f"📊 Status: {status.get('status')}")
        print(f"🎯 Current Step: {status.get('current_step')}")
        print(f"✅ Criteria Met: {status.get('criteria_met')}/10")
        print(f"📈 Eligibility Score: {status.get('eligibility_score', 0):.0%}")
        print(f"💡 Recommendation: {status.get('recommendation')}")
        print(f"📝 Questions Answered: {status.get('total_questions_answered')}")
        print()

    # ========== ШАГ 4: ПОЛУЧЕНИЕ ПОЛНЫХ ДАННЫХ ==========
    print("=" * 80)
    print("ШАГ 4: Получение полных данных петиции")
    print("=" * 80)
    print()

    get_cmd = MegaAgentCommand(
        user_id=user_id,
        command_type=CommandType.EB1,
        action="get",
        payload={"petition_id": petition_id},
    )

    response = await agent.handle_command(get_cmd, user_role)

    if response.success:
        petition_data = response.result or {}
        petition = petition_data.get("petition", {})

        print("👤 Персональная информация:")
        personal = petition.get("personal_info", {})
        if personal:
            print(f"  Имя: {personal.get('full_name')}")
            print(f"  Email: {personal.get('email')}")
            print(f"  Страна: {personal.get('current_country')}")
            print(f"  Виза: {personal.get('current_visa_status')}")
        print()

        print("🎓 Область экспертизы:")
        field = petition.get("field_of_expertise", {})
        if field:
            print(f"  Область: {field.get('field')}")
            print(f"  Опыт: {field.get('years_of_experience')} лет")
            print(f"  Должность: {field.get('current_position')}")
            print(f"  Образование: {field.get('education_level')}")
        print()

        print("📋 Доказательства по критериям:")
        criteria_evidence = petition.get("criteria_evidence", {})
        for criterion_key, evidence in criteria_evidence.items():
            if evidence.get("met"):
                criterion_name = criterion_key.upper()
                strength = evidence.get("strength_score", 0)
                count = evidence.get("evidence_count", 0)
                print(f"  ✅ {criterion_name}: {strength:.0%} сила ({count} доказательств)")
        print()

    # ========== ФИНАЛ ==========
    print("=" * 80)
    print("🎉 ДЕМО ЗАВЕРШЕНО!")
    print("=" * 80)
    print()
    print("📌 Что было продемонстрировано:")
    print("  1. ✅ Создание EB-1A петиции")
    print("  2. ✅ Интерактивный опрос по 10 критериям USCIS")
    print("  3. ✅ Автоматическая оценка соответствия")
    print("  4. ✅ Получение статуса и полных данных")
    print("  5. ✅ Сохранение в память (Episodic + Semantic)")
    print("  6. ✅ Полный audit trail всех операций")
    print()
    print("🚀 Система готова к использованию с реальными пользователями!")
    print()


if __name__ == "__main__":
    print("\n")
    asyncio.run(run_eb1_demo())
    print("\n")
