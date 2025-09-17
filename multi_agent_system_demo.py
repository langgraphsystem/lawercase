"""
Демонстрация полной мульти-агентной системы mega_agent_pro.

Показывает взаимодействие всех реализованных агентов:
- MegaAgent (оркестрация)
- CaseAgent (управление делами)
- WriterAgent (генерация документов)
- ValidatorAgent (валидация с самокоррекцией)
- SupervisorAgent (динамическая маршрутизация)
- RAGPipelineAgent (гибридный поиск)
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from core.memory.memory_manager import MemoryManager
from core.groupagents.mega_agent import MegaAgent, MegaAgentCommand, CommandType, UserRole
from core.groupagents.case_agent import CaseAgent
from core.groupagents.writer_agent import WriterAgent, DocumentRequest, DocumentType
from core.groupagents.validator_agent import ValidatorAgent, ValidationRequest, ValidationType
from core.groupagents.supervisor_agent import SupervisorAgent
from core.groupagents.rag_pipeline_agent import RAGPipelineAgent, SearchQuery, SearchStrategy
from core.groupagents.models import CaseType, CasePriority


async def demo_mega_agent_orchestration():
    """Демонстрация MegaAgent как центрального оркестратора"""
    print("🎯 === MegaAgent Orchestration Demo ===\n")

    # Инициализация системы
    memory = MemoryManager()
    mega_agent = MegaAgent(memory_manager=memory)

    # Установка роли пользователя
    user_id = "demo-lawyer-001"
    await mega_agent.set_user_role(user_id, UserRole.LAWYER)

    print("1. 🏢 Создание дела через MegaAgent...")

    # Команда создания дела
    create_case_command = MegaAgentCommand(
        user_id=user_id,
        command_type=CommandType.CASE,
        action="create",
        payload={
            "title": "Complex Immigration Case - Tech Startup Visa",
            "description": "H-1B visa application for international tech startup employees with complex documentation requirements",
            "case_type": CaseType.IMMIGRATION,
            "priority": CasePriority.HIGH,
            "client_id": "client-tech-startup-001",
            "assigned_lawyer": user_id,
            "tags": ["h1b", "startup", "tech", "complex"]
        }
    )

    case_response = await mega_agent.handle_command(create_case_command)
    print(f"✅ Дело создано через MegaAgent")
    print(f"   Case ID: {case_response.result.get('case_id', 'unknown')}")
    print(f"   Success: {case_response.success}")
    print()

    case_id = case_response.result.get("case_id")

    print("2. 📝 Генерация документа через MegaAgent...")

    # Команда генерации письма
    generate_letter_command = MegaAgentCommand(
        user_id=user_id,
        command_type=CommandType.GENERATE,
        action="letter",
        payload={
            "document_type": DocumentType.LETTER,
            "content_data": {
                "recipient": "USCIS Officer",
                "sender": "Legal Representative",
                "subject": "H-1B Visa Application - Supporting Documentation",
                "content": "We are submitting the H-1B visa application for our client's technology startup employees. This application includes comprehensive documentation demonstrating the specialized nature of the positions and the company's capacity to support these roles."
            },
            "case_id": case_id,
            "approval_required": True
        }
    )

    letter_response = await mega_agent.handle_command(generate_letter_command)
    print(f"✅ Письмо сгенерировано через MegaAgent")
    print(f"   Document ID: {letter_response.result.get('document_id', 'unknown')}")
    print(f"   Success: {letter_response.success}")
    print()

    return case_id, letter_response.result.get('document_id')


async def demo_supervisor_task_orchestration():
    """Демонстрация SupervisorAgent для сложных задач"""
    print("🎭 === SupervisorAgent Task Orchestration Demo ===\n")

    memory = MemoryManager()
    supervisor = SupervisorAgent(memory_manager=memory)
    user_id = "demo-supervisor-001"

    print("1. 🔍 Анализ сложной задачи...")

    # Сложная задача, требующая мульти-агентного подхода
    complex_task = "Prepare a comprehensive immigration case package including document generation, legal research, validation, and quality control for a tech startup H-1B application"

    analysis = await supervisor.analyze_task(complex_task)
    print(f"✅ Задача проанализирована")
    print(f"   Сложность: {analysis.complexity}")
    print(f"   Требуемые агенты: {[agent.value for agent in analysis.required_agents]}")
    print(f"   Стратегия выполнения: {analysis.execution_strategy}")
    print(f"   Уверенность: {analysis.confidence_score:.2f}")
    print()

    print("2. 📋 Декомпозиция задачи...")

    subtasks = await supervisor.decompose_task(complex_task, analysis)
    print(f"✅ Задача разбита на {len(subtasks)} подзадач:")
    for i, subtask in enumerate(subtasks, 1):
        print(f"   {i}. {subtask.description}")
        print(f"      Агент: {subtask.agent_type.value}, Приоритет: {subtask.priority}")
    print()

    print("3. 🚀 Оркестрация выполнения...")

    execution_result = await supervisor.orchestrate_workflow(complex_task, user_id)
    print(f"✅ Задача выполнена")
    print(f"   Успех: {execution_result.success}")
    print(f"   Время выполнения: {execution_result.execution_time:.2f}s")
    print(f"   Подзадач выполнено: {len(execution_result.results)}")

    if execution_result.final_result:
        print(f"   Общий успех: {execution_result.final_result.get('overall_success', False)}")
        print(f"   Успешных подзадач: {execution_result.final_result.get('successful_subtasks', 0)}")
    print()

    return execution_result


async def demo_writer_agent_features():
    """Демонстрация возможностей WriterAgent"""
    print("✍️ === WriterAgent Features Demo ===\n")

    memory = MemoryManager()
    writer = WriterAgent(memory_manager=memory)
    user_id = "demo-writer-001"

    print("1. 📄 Создание шаблона документа...")

    # Создание пользовательского шаблона
    template_data = {
        "name": "H-1B Cover Letter Template",
        "document_type": DocumentType.LETTER,
        "language": "en",
        "template_content": """
Dear {recipient},

Subject: H-1B Visa Petition for {employee_name} - {position_title}

I am writing to submit the H-1B visa petition for {employee_name}, who will be employed as {position_title} at {company_name}.

Key Details:
- Employee: {employee_name}
- Position: {position_title}
- Start Date: {start_date}
- Salary: {salary}

{additional_details}

We have prepared all required documentation and look forward to your favorable consideration of this petition.

Sincerely,
{sender_name}
{sender_title}
        """.strip(),
        "variables": ["recipient", "employee_name", "position_title", "company_name",
                     "start_date", "salary", "additional_details", "sender_name", "sender_title"]
    }

    template = await writer.acreate_template(template_data, user_id)
    print(f"✅ Шаблон создан: {template.name}")
    print(f"   Template ID: {template.template_id}")
    print()

    print("2. 📝 Генерация документа с шаблоном...")

    # Запрос на генерацию письма
    request = DocumentRequest(
        document_type=DocumentType.LETTER,
        template_id=template.template_id,
        content_data={
            "recipient": "USCIS Vermont Service Center",
            "employee_name": "Alex Chen",
            "position_title": "Senior Software Engineer",
            "company_name": "TechStart Innovations Inc.",
            "start_date": "January 1, 2024",
            "salary": "$95,000 annually",
            "additional_details": "The position requires specialized knowledge in machine learning and distributed systems.",
            "sender_name": "Sarah Johnson",
            "sender_title": "Immigration Attorney"
        },
        approval_required=True
    )

    document = await writer.agenerate_letter(request, user_id)
    print(f"✅ Документ сгенерирован")
    print(f"   Document ID: {document.document_id}")
    print(f"   Title: {document.title}")
    print(f"   Approval Status: {document.approval_status}")
    print()

    print("3. 📄 Генерация PDF...")

    pdf_path = await writer.agenerate_document_pdf(document.document_id, user_id)
    print(f"✅ PDF создан: {pdf_path}")
    print()

    return document


async def demo_validator_agent_capabilities():
    """Демонстрация возможностей ValidatorAgent"""
    print("🔍 === ValidatorAgent Capabilities Demo ===\n")

    memory = MemoryManager()
    validator = ValidatorAgent(memory_manager=memory)
    user_id = "demo-validator-001"

    print("1. ✅ Валидация данных дела...")

    # Валидация корректных данных дела
    valid_case_data = {
        "title": "Immigration Case - Software Engineer Visa",
        "description": "H-1B visa application for experienced software engineer with specialized skills in distributed systems and machine learning",
        "case_type": "immigration",
        "client_id": "client-001",
        "assigned_lawyer": "lawyer-001",
        "priority": "high"
    }

    validation_request = ValidationRequest(
        validation_type=ValidationType.CASE_DATA,
        data=valid_case_data,
        auto_fix=True
    )

    validation_result = await validator.avalidate(validation_request, user_id)
    print(f"✅ Валидация завершена")
    print(f"   Валидно: {validation_result.is_valid}")
    print(f"   Уверенность: {validation_result.confidence_score:.2f}")
    print(f"   Проблем найдено: {len(validation_result.issues)}")
    print(f"   Резюме: {validation_result.summary}")
    print()

    print("2. ❌ Валидация некорректных данных...")

    # Валидация данных с ошибками
    invalid_case_data = {
        "title": "",  # Пустое название
        "description": "Short",  # Слишком короткое описание
        "case_type": "invalid_type",  # Неправильный тип
        "client_id": "",  # Пустой client_id
        "priority": "medium"
    }

    invalid_request = ValidationRequest(
        validation_type=ValidationType.CASE_DATA,
        data=invalid_case_data,
        auto_fix=True
    )

    invalid_result = await validator.avalidate(invalid_request, user_id)
    print(f"✅ Валидация некорректных данных завершена")
    print(f"   Валидно: {invalid_result.is_valid}")
    print(f"   Уверенность: {invalid_result.confidence_score:.2f}")
    print(f"   Проблем найдено: {len(invalid_result.issues)}")
    print(f"   Автоисправления: {len(invalid_result.corrections)}")

    for issue in invalid_result.issues[:3]:  # Показываем первые 3 проблемы
        print(f"   - {issue.message} (Severity: {issue.severity})")
    print()

    print("3. 🤝 MAGCC Consensus для спорного случая...")

    from core.groupagents.validator_agent import ConsensusRequest

    # Спорный вопрос для консенсуса
    consensus_request = ConsensusRequest(
        question="What is the best approach for this complex H-1B case with multiple technical specializations?",
        options=[
            "Focus on AI/ML expertise with detailed technical documentation",
            "Emphasize distributed systems experience with architecture examples",
            "Combine both specializations with comprehensive portfolio"
        ],
        validation_data=valid_case_data,
        required_confidence=0.7
    )

    consensus_result = await validator.amagcc_consensus(consensus_request, user_id)
    print(f"✅ MAGCC консенсус завершен")
    print(f"   Консенсус достигнут: {consensus_result.achieved}")
    print(f"   Выбранный вариант: {consensus_result.selected_option}")
    print(f"   Уверенность: {consensus_result.confidence:.2f}")
    print(f"   Итераций: {consensus_result.iterations}")
    print()

    return validation_result, consensus_result


async def demo_rag_pipeline_search():
    """Демонстрация RAGPipelineAgent"""
    print("🔍 === RAGPipelineAgent Search Demo ===\n")

    memory = MemoryManager()
    rag = RAGPipelineAgent(memory_manager=memory)
    user_id = "demo-rag-001"

    print("1. 📄 Создание и обработка тестового документа...")

    # Создание тестового документа
    test_doc_content = """
    H-1B Visa Requirements and Process

    The H-1B visa is a non-immigrant visa that allows U.S. companies to employ foreign workers
    in specialty occupations that require specialized knowledge and a bachelor's degree or higher
    in the specific specialty, or its equivalent.

    Key Requirements:
    - Bachelor's degree or higher in a specific specialty
    - Job offer from a U.S. employer
    - Labor Condition Application (LCA) approval
    - Specialized knowledge in the field

    Application Process:
    1. Employer files Labor Condition Application (LCA)
    2. Employer submits Form I-129 petition
    3. Employee applies for visa at consulate (if outside U.S.)
    4. Entry into the United States

    Technical Positions:
    Software engineers, data scientists, and machine learning engineers are common H-1B recipients
    due to the specialized nature of their work and educational requirements.
    """

    # Создание временного файла
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_doc_content)
        temp_file_path = f.name

    try:
        # Обработка документа
        processed_doc = await rag.aprocess_document(temp_file_path, user_id=user_id)
        print(f"✅ Документ обработан")
        print(f"   Document ID: {processed_doc.document_id}")
        print(f"   Чанков создано: {len(processed_doc.chunks)}")
        print(f"   Длина содержимого: {len(processed_doc.content)} символов")
        print()

        print("2. 🔍 Гибридный поиск...")

        # Поисковый запрос
        search_query = SearchQuery(
            query_text="software engineer H-1B requirements technical positions",
            strategy=SearchStrategy.HYBRID,
            limit=5
        )

        search_results = await rag.asearch(search_query, user_id)
        print(f"✅ Поиск завершен")
        print(f"   Найдено результатов: {len(search_results.results)}")
        print(f"   Время поиска: {search_results.search_time:.3f}s")
        print(f"   Стратегия: {search_results.strategy_used}")
        print()

        if search_results.results:
            print("   Топ результаты:")
            for i, result in enumerate(search_results.results[:3], 1):
                print(f"   {i}. Score: {result.score:.3f}")
                print(f"      {result.content[:100]}...")
                if result.highlights:
                    print(f"      Highlights: {result.highlights[0][:80]}...")
        print()

        print("3. 🎯 Семантический поиск...")

        # Семантический поиск
        semantic_query = SearchQuery(
            query_text="machine learning data scientist visa application",
            strategy=SearchStrategy.SEMANTIC_SIMILARITY,
            limit=3
        )

        semantic_results = await rag.asearch(semantic_query, user_id)
        print(f"✅ Семантический поиск завершен")
        print(f"   Найдено результатов: {len(semantic_results.results)}")
        print(f"   Агрегированное содержимое доступно: {semantic_results.aggregated_content is not None}")
        print()

    finally:
        # Очистка временного файла
        Path(temp_file_path).unlink(missing_ok=True)

    return search_results


async def demo_full_workflow_integration():
    """Демонстрация полной интеграции всех агентов"""
    print("🌐 === Full Multi-Agent Workflow Integration ===\n")

    memory = MemoryManager()
    mega_agent = MegaAgent(memory_manager=memory)
    user_id = "demo-workflow-001"

    # Установка роли
    await mega_agent.set_user_role(user_id, UserRole.LAWYER)

    print("1. 🎯 Создание комплексного дела...")

    # Команда создания комплексного дела
    complex_case_command = MegaAgentCommand(
        user_id=user_id,
        command_type=CommandType.CASE,
        action="create",
        payload={
            "title": "Multi-National Tech Company H-1B Batch Processing",
            "description": "Processing multiple H-1B applications for a tech company with employees from various countries requiring different documentation strategies",
            "case_type": CaseType.IMMIGRATION,
            "priority": CasePriority.HIGH,
            "client_id": "client-multinational-tech",
            "assigned_lawyer": user_id,
            "tags": ["h1b", "batch", "multinational", "tech", "complex"],
            "metadata": {
                "employee_count": 25,
                "countries": ["India", "China", "Brazil", "Germany", "UK"],
                "specializations": ["AI/ML", "DevOps", "Frontend", "Backend", "Data Science"]
            }
        }
    )

    case_response = await mega_agent.handle_command(complex_case_command)
    print(f"✅ Комплексное дело создано")
    print(f"   Case ID: {case_response.result.get('case_id')}")
    print()

    print("2. 📋 Поиск существующих дел...")

    # Поиск связанных дел
    search_command = MegaAgentCommand(
        user_id=user_id,
        command_type=CommandType.CASE,
        action="search",
        payload={
            "query": {
                "case_type": "immigration",
                "tags": ["h1b"],
                "limit": 5
            }
        }
    )

    search_response = await mega_agent.handle_command(search_command)
    print(f"✅ Поиск дел завершен")
    case_result = search_response.result.get('case_result', {}) if search_response.result else {}
    print(f"   Найдено дел: {case_result.get('count', 0)}")
    print()

    print("3. 📝 Генерация пакета документов...")

    # Генерация cover letter
    letter_command = MegaAgentCommand(
        user_id=user_id,
        command_type=CommandType.GENERATE,
        action="letter",
        payload={
            "document_type": DocumentType.LETTER,
            "content_data": {
                "recipient": "USCIS California Service Center",
                "sender": "Immigration Law Firm",
                "subject": "H-1B Petition Package - Multi-National Tech Company",
                "content": "We are submitting a comprehensive package of H-1B petitions for 25 highly skilled technology professionals from various countries. Each application demonstrates the specialized nature of their roles and the company's commitment to supporting these critical positions."
            },
            "case_id": case_response.result.get('case_id'),
            "approval_required": False
        }
    )

    letter_response = await mega_agent.handle_command(letter_command)
    print(f"✅ Cover letter сгенерирован")
    print(f"   Document ID: {letter_response.result.get('document_id')}")
    print()

    print("4. 📊 Проверка статистики системы...")

    # Получение статистики всех агентов
    mega_stats = await mega_agent.get_stats()
    health_check = await mega_agent.health_check()

    print(f"✅ Статистика системы:")
    print(f"   Всего команд выполнено: {mega_stats.get('total_commands', 0)}")
    print(f"   Статистика команд: {mega_stats.get('command_stats', {})}")
    print(f"   Зарегистрированных пользователей: {mega_stats.get('registered_users', 0)}")
    print(f"   Статус системы: {health_check.get('status', 'unknown')}")
    print()

    return {
        "case_id": case_response.result.get('case_id'),
        "document_id": letter_response.result.get('document_id'),
        "stats": mega_stats,
        "health": health_check
    }


async def main():
    """Главная функция демонстрации"""
    print("🚀 MEGA AGENT PRO - Complete Multi-Agent System Demonstration")
    print("=" * 70)
    print()

    try:
        # 1. Демонстрация центрального оркестратора
        case_id, doc_id = await demo_mega_agent_orchestration()

        # 2. Демонстрация супервизора задач
        workflow_result = await demo_supervisor_task_orchestration()

        # 3. Демонстрация генерации документов
        generated_doc = await demo_writer_agent_features()

        # 4. Демонстрация валидации
        validation_result, consensus = await demo_validator_agent_capabilities()

        # 5. Демонстрация RAG поиска
        search_results = await demo_rag_pipeline_search()

        # 6. Демонстрация полной интеграции
        integration_results = await demo_full_workflow_integration()

        print("🎉 === Complete System Demo Results ===")
        print(f"✅ MegaAgent Orchestration: Created case {case_id}, document {doc_id}")
        print(f"✅ SupervisorAgent: Executed workflow with {len(workflow_result.results)} subtasks")
        print(f"✅ WriterAgent: Generated document {generated_doc.document_id}")
        print(f"✅ ValidatorAgent: Validation confidence {validation_result.confidence_score:.2f}")
        print(f"✅ RAGPipelineAgent: Found {len(search_results.results)} search results")
        print(f"✅ Full Integration: System health {integration_results['health']['status']}")
        print()
        print("🌟 All agents successfully demonstrated!")
        print("🔗 Multi-agent coordination and workflow integration working!")
        print("📊 Complete audit trail and memory integration functional!")

    except Exception as e:
        print(f"❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())