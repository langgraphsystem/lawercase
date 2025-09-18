#!/usr/bin/env python3
"""
Enhanced Agents Integration Demo для mega_agent_pro.

Демонстрирует интеграцию всех улучшенных агентов с новой LLM/RAG архитектурой:
1. EnhancedCaseAgent - AI-powered управление делами
2. EnhancedWriterAgent - Интеллектуальная генерация документов
3. EnhancedValidatorAgent - AI валидация с автокоррекцией
4. Совместная работа агентов в реальных сценариях
5. End-to-end workflow демонстрация

Запуск:
    python enhanced_agents_demo.py
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты базовой архитектуры
from core.llm_router import create_llm_router
from core.simple_embedder import create_simple_embedder
from core.basic_rag import create_basic_rag

# Импорты улучшенных агентов
from core.groupagents.enhanced_case_agent import (
    create_enhanced_case_agent,
    CaseAnalysisRequest,
    CaseSearchRequest
)

from core.groupagents.enhanced_writer_agent import (
    create_enhanced_writer_agent,
    DocumentGenerationRequest,
    DocumentType,
    Language
)

from core.groupagents.enhanced_validator_agent import (
    create_enhanced_validator_agent,
    ValidationRequest,
    ValidationType
)

# Импорты моделей
from core.groupagents.models import CaseType, CaseStatus


async def setup_shared_infrastructure():
    """Настройка общей AI инфраструктуры"""
    print("🔧 Настройка общей AI инфраструктуры...")

    # Общая конфигурация для всех компонентов
    ai_config = {
        "providers": {
            "openai": {"enabled": True, "api_key": "demo-key"},
            "gemini": {"enabled": True, "api_key": "demo-key"},
            "claude": {"enabled": True, "api_key": "demo-key"},
            "mock": {"enabled": True, "failure_rate": 0.05}
        }
    }

    # Создаем общие компоненты
    llm_router = await create_llm_router(ai_config)
    embedder = await create_simple_embedder(ai_config)
    rag_system = await create_basic_rag(embedder, llm_router)

    print("   ✅ LLM Router инициализирован")
    print("   ✅ Simple Embedder готов")
    print("   ✅ Basic RAG система активна")

    return llm_router, embedder, rag_system


async def setup_agents(llm_router, embedder, rag_system):
    """Создание всех улучшенных агентов"""
    print("\n🤖 Создание улучшенных агентов...")

    # Создаем агентов с общей инфраструктурой
    case_agent = await create_enhanced_case_agent(llm_router, embedder, rag_system)
    writer_agent = await create_enhanced_writer_agent(llm_router, embedder, rag_system)
    validator_agent = await create_enhanced_validator_agent(llm_router, embedder, rag_system)

    print("   ✅ EnhancedCaseAgent готов")
    print("   ✅ EnhancedWriterAgent готов")
    print("   ✅ EnhancedValidatorAgent готов")

    return case_agent, writer_agent, validator_agent


async def demo_case_agent(case_agent):
    """Демонстрация EnhancedCaseAgent"""
    print("\n📁 === Enhanced Case Agent Demo ===")

    # Создаем тестовое дело
    case_data = {
        "title": "Трудовой спор - незаконное увольнение",
        "description": """
        Клиент обратился по поводу незаконного увольнения с предыдущего места работы.
        Работодатель уволил его без предупреждения и не выплатил компенсацию.
        Требуется составить иск в суд и подготовить необходимые документы.
        """,
        "case_type": CaseType.CIVIL,
        "priority": "high",
        "client_id": "client_001",
        "assigned_lawyer": "lawyer_petrova",
        "tags": ["трудовое право", "увольнение", "компенсация"]
    }

    # Создаем дело
    result = await case_agent.create_case(case_data)
    print(f"   📝 Дело создано: {result.case_id[:8]}... (success: {result.success})")

    if result.success:
        case_id = result.case_id

        # AI анализ дела
        analysis_request = CaseAnalysisRequest(
            case_id=case_id,
            analysis_type="strategy",
            priority="high"
        )

        analysis = await case_agent.analyze_case(analysis_request)
        if analysis:
            print(f"   🧠 AI анализ (уверенность: {analysis.confidence:.2f}):")
            print(f"      {analysis.analysis[:100]}...")
            print(f"      Рекомендации: {len(analysis.recommendations)}")

        # Семантический поиск дел
        search_request = CaseSearchRequest(
            query="трудовые споры увольнение",
            search_type="semantic",
            max_results=3
        )

        search_results = await case_agent.search_cases(search_request)
        print(f"   🔍 Найдено похожих дел: {len(search_results)}")

        # Получение рекомендаций
        recommendations = await case_agent.get_case_recommendations(case_id)
        print(f"   💡 AI рекомендации: {len(recommendations)}")
        for i, rec in enumerate(recommendations[:2], 1):
            print(f"      {i}. {rec.description[:60]}...")

        return case_id

    return None


async def demo_writer_agent(writer_agent, case_id=None):
    """Демонстрация EnhancedWriterAgent"""
    print("\n📝 === Enhanced Writer Agent Demo ===")

    # Запрос на генерацию искового заявления
    generation_request = DocumentGenerationRequest(
        document_type=DocumentType.MOTION,
        title="Исковое заявление о восстановлении на работе",
        content_data={
            "plaintiff": "Иванов Иван Иванович",
            "defendant": "ООО 'Технологии Будущего'",
            "claim": "Восстановление на работе и взыскание заработной платы",
            "grounds": "Незаконное увольнение без предупреждения",
            "compensation": "150000 рублей",
            "case_id": case_id
        },
        style="formal",
        language=Language.RUSSIAN,
        use_rag=True,
        max_length=1500
    )

    # Генерируем документ
    doc_result = await writer_agent.generate_document(generation_request)
    print(f"   📄 Документ сгенерирован (ID: {doc_result.document_id[:8]}...)")
    print(f"      Качество: {doc_result.quality_score:.2f}")
    print(f"      Слов: {doc_result.word_count}")
    print(f"      Время: {doc_result.generation_time:.2f}с")

    if doc_result.sources:
        print(f"      Источники: {', '.join(doc_result.sources[:2])}")

    # Демонстрируем улучшение документа
    if doc_result.success and doc_result.quality_score < 0.9:
        print("\n   🔧 Улучшение документа...")
        improved_result = await writer_agent.improve_document(
            doc_result.document_id,
            "Добавить больше юридических обоснований и ссылок на законодательство"
        )

        if improved_result.success:
            print(f"      ✨ Улучшенная версия (ID: {improved_result.document_id[:8]}...)")
            print(f"      Новое качество: {improved_result.quality_score:.2f}")

    # Демонстрируем работу с шаблонами
    print("\n   📋 Генерация по шаблону...")
    template_result = await writer_agent.generate_from_template(
        "letter_formal",
        {
            "recipient": "Трудовая инспекция",
            "sender": "Юридическая фирма 'ПравоЗащита'",
            "subject": "Уведомление о нарушении трудовых прав",
            "main_content": "Сообщаем о факте незаконного увольнения нашего клиента"
        }
    )

    if template_result.success:
        print(f"      📨 Письмо создано (качество: {template_result.quality_score:.2f})")

    return doc_result.document_id if doc_result.success else None


async def demo_validator_agent(validator_agent, document_id=None):
    """Демонстрация EnhancedValidatorAgent"""
    print("\n✅ === Enhanced Validator Agent Demo ===")

    # Тестовый документ для валидации
    test_document = """
    Исковое заявление

    В Центральный районный суд г. Москвы

    От: Иванов И.И.
    К: ООО "Компания"

    Прошу восстановить меня на работе в связи с незаконным увольнением.
    Работодатель уволил меня 15 марта без предупреждения.

    Подпись: И.И. Иванов
    """

    # Валидация структуры документа
    print("   📋 Валидация структуры документа...")
    structure_validation = await validator_agent.validate_document_structure(test_document)

    print(f"      Общая оценка: {structure_validation.overall_score:.2f}")
    print(f"      Прошел валидацию: {'✅' if structure_validation.passed else '❌'}")
    print(f"      Проблем найдено: {len(structure_validation.issues)}")

    for issue in structure_validation.issues[:3]:
        print(f"        - {issue.severity}: {issue.description[:50]}...")

    # Валидация правового соответствия
    print("\n   ⚖️ Валидация правового соответствия...")
    legal_request = ValidationRequest(
        content=test_document,
        validation_type=ValidationType.LEGAL_COMPLIANCE,
        context={"jurisdiction": "RU"},
        auto_correct=True
    )

    legal_validation = await validator_agent.validate(legal_request)

    print(f"      Правовое соответствие: {legal_validation.overall_score:.2f}")
    print(f"      Время валидации: {legal_validation.validation_time:.2f}с")

    if legal_validation.corrected_content:
        print("      🔧 Автокоррекция выполнена")

    # Валидация с улучшением
    print("\n   ✨ Валидация с автоматическим улучшением...")
    final_validation, improved_content = await validator_agent.validate_and_improve(
        test_document,
        ValidationType.CONTENT_QUALITY
    )

    print(f"      Финальная оценка: {final_validation.overall_score:.2f}")
    print(f"      Рекомендации: {len(final_validation.recommendations)}")

    for rec in final_validation.recommendations[:2]:
        print(f"        💡 {rec}")

    return final_validation


async def demo_integrated_workflow(case_agent, writer_agent, validator_agent):
    """Демонстрация интегрированного workflow"""
    print("\n🔄 === Integrated Workflow Demo ===")
    print("Полный цикл: Дело → Документ → Валидация → Улучшение")

    # 1. Создаем дело
    print("\n1️⃣ Создание дела...")
    case_data = {
        "title": "Корпоративный спор - нарушение договора поставки",
        "description": """
        Компания-поставщик нарушила условия договора поставки оборудования,
        поставив товар ненадлежащего качества с опозданием на 2 месяца.
        Требуется взыскание неустойки и возмещение убытков.
        """,
        "case_type": "CORPORATE",
        "priority": "high",
        "client_id": "client_corp_001"
    }

    case_result = await case_agent.create_case(case_data)
    if not case_result.success:
        print("   ❌ Не удалось создать дело")
        return

    case_id = case_result.case_id
    print(f"   ✅ Дело создано: {case_id[:8]}...")

    # 2. AI анализ дела
    print("\n2️⃣ AI анализ дела...")
    analysis = await case_agent.analyze_case(CaseAnalysisRequest(
        case_id=case_id,
        analysis_type="strategy"
    ))

    if analysis:
        print(f"   🧠 Анализ выполнен (уверенность: {analysis.confidence:.2f})")
        print(f"      Рекомендации: {len(analysis.recommendations)}")

    # 3. Генерация претензии
    print("\n3️⃣ Генерация претензии...")
    doc_request = DocumentGenerationRequest(
        document_type=DocumentType.NOTICE,
        title="Претензия о нарушении договора поставки",
        content_data={
            "supplier": "ООО 'ТехПоставка'",
            "buyer": "ООО 'ПромТех'",
            "contract_number": "№ 145/2024",
            "violation": "Поставка некачественного оборудования с нарушением сроков",
            "damages": "500000 рублей",
            "case_id": case_id
        },
        use_rag=True,
        auto_correct=False
    )

    doc_result = await writer_agent.generate_document(doc_request)
    if not doc_result.success:
        print("   ❌ Не удалось сгенерировать документ")
        return

    print(f"   📝 Претензия создана (качество: {doc_result.quality_score:.2f})")

    # 4. Валидация документа
    print("\n4️⃣ Валидация претензии...")
    validation_request = ValidationRequest(
        content=doc_result.content,
        validation_type=ValidationType.LEGAL_COMPLIANCE,
        auto_correct=True
    )

    validation = await validator_agent.validate(validation_request)
    print(f"   ✅ Валидация завершена (оценка: {validation.overall_score:.2f})")
    print(f"      Проблем: {len(validation.issues)}")

    # 5. Улучшение документа если нужно
    if validation.overall_score < 0.8:
        print("\n5️⃣ Улучшение документа...")
        improved = await writer_agent.improve_document(
            doc_result.document_id,
            "Устранить выявленные валидатором проблемы и усилить правовые обоснования"
        )

        if improved.success:
            print(f"   ✨ Документ улучшен (новая оценка: {improved.quality_score:.2f})")

            # Повторная валидация
            final_validation = await validator_agent.validate(ValidationRequest(
                content=improved.content,
                validation_type=ValidationType.LEGAL_COMPLIANCE
            ))

            print(f"   🔄 Финальная валидация: {final_validation.overall_score:.2f}")

    # 6. Обновление дела с результатами
    print("\n6️⃣ Обновление дела...")
    case_update = await case_agent.update_case(case_id, {
        "status": CaseStatus.IN_PROGRESS,
        "metadata": {
            "documents_generated": [doc_result.document_id],
            "last_action": "pretension_sent",
            "workflow_completed": True
        }
    })

    if case_update.success:
        print("   ✅ Дело обновлено с результатами workflow")

    # 7. Финальная статистика
    print("\n7️⃣ Итоговая статистика...")
    case_stats = case_agent.get_stats()
    writer_stats = writer_agent.get_stats()
    validator_stats = validator_agent.get_stats()

    print(f"   📊 CaseAgent: {case_stats['total_cases']} дел, {case_stats['analyses_performed']} анализов")
    print(f"   📊 WriterAgent: {writer_stats['documents_generated']} документов")
    print(f"   📊 ValidatorAgent: {validator_stats['validations_performed']} валидаций")

    print("\n🎉 Интегрированный workflow завершен успешно!")


async def demo_advanced_features(case_agent, writer_agent, validator_agent):
    """Демонстрация продвинутых возможностей"""
    print("\n🚀 === Advanced Features Demo ===")

    # Массовая обработка
    print("📦 Массовая обработка документов...")

    # Создаем несколько дел одновременно
    cases_data = [
        {
            "title": "Семейный спор - раздел имущества",
            "description": "Раздел совместно нажитого имущества супругов",
            "case_type": "FAMILY",
            "priority": "MEDIUM"
        },
        {
            "title": "Административное правонарушение - штраф ГИБДД",
            "description": "Обжалование необоснованного штрафа за превышение скорости",
            "case_type": "ADMINISTRATIVE",
            "priority": "LOW"
        },
        {
            "title": "Уголовное дело - кража",
            "description": "Защита подозреваемого в краже имущества",
            "case_type": "CRIMINAL",
            "priority": "CRITICAL"
        }
    ]

    created_cases = []
    for case_data in cases_data:
        result = await case_agent.create_case(case_data)
        if result.success:
            created_cases.append(result.case_id)

    print(f"   ✅ Создано дел: {len(created_cases)}")

    # Семантический поиск по всем делам
    print("\n🔍 Семантический поиск...")
    search_queries = [
        "имущественные споры",
        "административные штрафы",
        "уголовная защита"
    ]

    for query in search_queries:
        results = await case_agent.search_cases(CaseSearchRequest(
            query=query,
            search_type="semantic",
            max_results=5
        ))
        print(f"   🎯 '{query}': найдено {len(results)} дел")

    # Многоязычная генерация
    print("\n🌐 Многоязычная генерация документов...")
    multilang_request = DocumentGenerationRequest(
        document_type=DocumentType.LETTER,
        title="Business Correspondence",
        content_data={
            "recipient": "International Law Firm",
            "subject": "Legal consultation request",
            "content": "We need legal advice on international contract law"
        },
        language=Language.ENGLISH,
        style="business"
    )

    multilang_doc = await writer_agent.generate_document(multilang_request)
    if multilang_doc.success:
        print(f"   🇺🇸 English document generated (quality: {multilang_doc.quality_score:.2f})")

    # Автоматический перевод
    if multilang_doc.success:
        translation = await writer_agent.translate_document(multilang_doc.document_id, Language.RUSSIAN)
        if translation.success:
            print(f"   🇷🇺 Translated to Russian (quality: {translation.quality_score:.2f})")

    # Пакетная валидация
    print("\n🔍 Пакетная валидация...")
    test_docs = [
        "Краткий документ без структуры",
        """
        ДОГОВОР КУПЛИ-ПРОДАЖИ

        Продавец: Иванов И.И.
        Покупатель: Петров П.П.
        Предмет: Автомобиль Toyota Camry 2020 года
        Цена: 1,500,000 рублей

        Подписи сторон
        """,
        """
        Уважаемые коллеги!

        Направляем вам документы по делу № 12345.
        Просим рассмотреть в кратчайшие сроки.

        С уважением,
        Юридическая фирма
        """
    ]

    validation_results = []
    for i, doc in enumerate(test_docs, 1):
        validation = await validator_agent.validate(ValidationRequest(
            content=doc,
            validation_type=ValidationType.CONTENT_QUALITY,
            auto_correct=True
        ))
        validation_results.append(validation)
        print(f"   📋 Документ {i}: оценка {validation.overall_score:.2f}")

    avg_quality = sum(v.overall_score for v in validation_results) / len(validation_results)
    print(f"   📊 Средняя оценка качества: {avg_quality:.2f}")


async def main():
    """Главная функция демонстрации"""
    print("🤖 MEGA AGENT PRO - Enhanced Agents Integration Demo")
    print("=" * 70)

    try:
        # 1. Настройка инфраструктуры
        llm_router, embedder, rag_system = await setup_shared_infrastructure()

        # 2. Создание агентов
        case_agent, writer_agent, validator_agent = await setup_agents(llm_router, embedder, rag_system)

        # 3. Демонстрация отдельных агентов
        case_id = await demo_case_agent(case_agent)
        document_id = await demo_writer_agent(writer_agent, case_id)
        validation_result = await demo_validator_agent(validator_agent, document_id)

        # 4. Интегрированный workflow
        await demo_integrated_workflow(case_agent, writer_agent, validator_agent)

        # 5. Продвинутые возможности
        await demo_advanced_features(case_agent, writer_agent, validator_agent)

        print("\n✅ === Enhanced Agents Demo Complete ===")

        print("\n🎯 Ключевые улучшения:")
        print("   🤖 Интеграция с LLM Router для качественной AI генерации")
        print("   🧠 RAG система для контекстно-зависимой работы")
        print("   🔍 Семантический поиск по делам и документам")
        print("   ✅ AI валидация с автоматическим исправлением")
        print("   📊 Интеллектуальная аналитика и рекомендации")
        print("   🌐 Многоязычная поддержка")
        print("   🔄 End-to-end автоматизированные workflow")

        print("\n🚀 Возможности системы:")
        print("   📁 AI-powered управление делами с анализом")
        print("   📝 Интеллектуальная генерация юридических документов")
        print("   ✅ Комплексная валидация с улучшениями")
        print("   🔍 Семантический поиск и аналитика")
        print("   🤝 Совместная работа агентов")
        print("   📊 Мониторинг качества и производительности")

        print("\n📊 Финальная статистика:")
        case_stats = case_agent.get_stats()
        writer_stats = writer_agent.get_stats()
        validator_stats = validator_agent.get_stats()

        print(f"   📁 CaseAgent: {case_stats['total_cases']} дел, {case_stats['analyses_performed']} анализов")
        print(f"   📝 WriterAgent: {writer_stats['documents_generated']} документов")
        print(f"   ✅ ValidatorAgent: {validator_stats['validations_performed']} валидаций")

        print("\n🎉 Интеграция агентов с LLM/RAG архитектурой завершена успешно!")

    except Exception as e:
        print(f"❌ Demo error: {e}")
        logger.exception("Demo failed")


if __name__ == "__main__":
    asyncio.run(main())