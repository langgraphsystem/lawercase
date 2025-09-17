"""
Comprehensive Agent Tests для mega_agent_pro.

Содержит тесты для всех основных агентов:
- MegaAgent (central orchestrator)
- SupervisorAgent (task routing)
- CaseAgent (case management)
- WriterAgent (document generation)
- ValidatorAgent (validation)
- RAGPipelineAgent (search & retrieval)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from .test_framework import TestAssertion, TestType, TestSeverity, test_case, performance_test

# Импорты агентов для тестирования
try:
    from ..groupagents.mega_agent import MegaAgent, MegaAgentCommand, UserRole
    from ..groupagents.supervisor_agent import SupervisorAgent, TaskRequest
    from ..groupagents.case_agent import CaseAgent, CaseRequest, CaseData
    from ..groupagents.writer_agent import WriterAgent, DocumentRequest
    from ..groupagents.validator_agent import ValidatorAgent, ValidationRequest
    from ..groupagents.rag_pipeline_agent import RAGPipelineAgent, SearchQuery
    from ..memory.memory_manager import MemoryManager
except ImportError as e:
    print(f"Warning: Could not import agents for testing: {e}")


class MegaAgentTests:
    """Тесты для MegaAgent."""

    @test_case("mega_agent_initialization", TestType.UNIT, TestSeverity.CRITICAL)
    async def test_initialization(self, assert_helper: TestAssertion):
        """Тест инициализации MegaAgent."""
        memory_manager = MemoryManager()
        mega_agent = MegaAgent(memory_manager=memory_manager)

        assert_helper.assert_not_none(mega_agent, "MegaAgent should be initialized")
        assert_helper.assert_not_none(mega_agent.memory, "Memory manager should be set")
        assert_helper.assert_equal(mega_agent.agent_id.startswith("mega_agent_"), True, "Agent ID should have correct prefix")

    @test_case("mega_agent_command_routing", TestType.INTEGRATION, TestSeverity.HIGH)
    async def test_command_routing(self, assert_helper: TestAssertion):
        """Тест маршрутизации команд."""
        memory_manager = MemoryManager()
        mega_agent = MegaAgent(memory_manager=memory_manager)

        # Тест команды /status
        command = MegaAgentCommand(command="/status", args=[], user_id="test_user")
        response = await mega_agent.handle_command(command, UserRole.ADMIN)

        assert_helper.assert_not_none(response, "Response should not be None")
        assert_helper.assert_equal(response.success, True, "Status command should succeed")
        assert_helper.assert_in("status", response.message.lower(), "Response should contain status info")

    @test_case("mega_agent_rbac_enforcement", TestType.SECURITY, TestSeverity.CRITICAL)
    async def test_rbac_enforcement(self, assert_helper: TestAssertion):
        """Тест RBAC enforcement."""
        memory_manager = MemoryManager()
        mega_agent = MegaAgent(memory_manager=memory_manager)

        # Тест доступа клиента к административным командам
        admin_command = MegaAgentCommand(command="/admin", args=[], user_id="test_client")
        response = await mega_agent.handle_command(admin_command, UserRole.CLIENT)

        assert_helper.assert_equal(response.success, False, "Client should not access admin commands")
        assert_helper.assert_in("permission", response.message.lower(), "Response should mention permissions")

    @performance_test("mega_agent_command_performance", max_duration_ms=100, iterations=50)
    async def test_command_performance(self):
        """Performance тест для обработки команд."""
        memory_manager = MemoryManager()
        mega_agent = MegaAgent(memory_manager=memory_manager)

        command = MegaAgentCommand(command="/status", args=[], user_id="test_user")
        await mega_agent.handle_command(command, UserRole.ADMIN)


class SupervisorAgentTests:
    """Тесты для SupervisorAgent."""

    @test_case("supervisor_agent_initialization", TestType.UNIT, TestSeverity.CRITICAL)
    async def test_initialization(self, assert_helper: TestAssertion):
        """Тест инициализации SupervisorAgent."""
        memory_manager = MemoryManager()
        supervisor = SupervisorAgent(memory_manager=memory_manager)

        assert_helper.assert_not_none(supervisor, "SupervisorAgent should be initialized")
        assert_helper.assert_not_none(supervisor.memory, "Memory manager should be set")

    @test_case("supervisor_task_analysis", TestType.INTEGRATION, TestSeverity.HIGH)
    async def test_task_analysis(self, assert_helper: TestAssertion):
        """Тест анализа задач."""
        memory_manager = MemoryManager()
        supervisor = SupervisorAgent(memory_manager=memory_manager)

        task_description = "Create a new legal case and generate a contract document"
        result = await supervisor.orchestrate_workflow(task_description, "test_user")

        assert_helper.assert_not_none(result, "Workflow result should not be None")
        assert_helper.assert_greater(len(result.execution_steps), 0, "Should have execution steps")
        assert_helper.assert_not_none(result.workflow_id, "Should have workflow ID")

    @test_case("supervisor_multi_agent_coordination", TestType.INTEGRATION, TestSeverity.HIGH)
    async def test_multi_agent_coordination(self, assert_helper: TestAssertion):
        """Тест координации нескольких агентов."""
        memory_manager = MemoryManager()
        supervisor = SupervisorAgent(memory_manager=memory_manager)

        # Задача, требующая нескольких агентов
        task_description = "Analyze legal document, validate content, and create summary"
        result = await supervisor.orchestrate_workflow(task_description, "test_user")

        assert_helper.assert_not_none(result, "Multi-agent result should not be None")
        assert_helper.assert_equal(result.status, "completed", "Workflow should complete")


class CaseAgentTests:
    """Тесты для CaseAgent."""

    @test_case("case_agent_crud_operations", TestType.FUNCTIONAL, TestSeverity.HIGH)
    async def test_crud_operations(self, assert_helper: TestAssertion):
        """Тест CRUD операций для дел."""
        memory_manager = MemoryManager()
        case_agent = CaseAgent(memory_manager=memory_manager)

        # Создание дела
        case_request = CaseRequest(
            title="Test Legal Case",
            description="Test case for unit testing",
            case_type="contract_dispute",
            priority="high",
            client_id="test_client",
            assigned_lawyer="test_lawyer"
        )

        create_response = await case_agent.acreate_case(case_request, "test_user")
        assert_helper.assert_not_none(create_response, "Create response should not be None")
        assert_helper.assert_equal(create_response.success, True, "Case creation should succeed")

        case_id = create_response.case_id
        assert_helper.assert_not_none(case_id, "Case ID should be generated")

        # Чтение дела
        get_response = await case_agent.aget_case(case_id, "test_user")
        assert_helper.assert_not_none(get_response, "Get response should not be None")
        assert_helper.assert_equal(get_response.case_data.title, "Test Legal Case", "Case title should match")

        # Обновление дела
        update_data = {"status": "in_progress", "priority": "medium"}
        update_response = await case_agent.aupdate_case(case_id, update_data, "test_user")
        assert_helper.assert_equal(update_response.success, True, "Case update should succeed")

        # Проверка обновления
        updated_case = await case_agent.aget_case(case_id, "test_user")
        assert_helper.assert_equal(updated_case.case_data.status, "in_progress", "Status should be updated")

    @test_case("case_agent_search_functionality", TestType.FUNCTIONAL, TestSeverity.MEDIUM)
    async def test_search_functionality(self, assert_helper: TestAssertion):
        """Тест поиска дел."""
        memory_manager = MemoryManager()
        case_agent = CaseAgent(memory_manager=memory_manager)

        # Создаем несколько тестовых дел
        cases_data = [
            {"title": "Contract Dispute A", "case_type": "contract_dispute", "priority": "high"},
            {"title": "Employment Issue B", "case_type": "employment", "priority": "medium"},
            {"title": "Contract Dispute C", "case_type": "contract_dispute", "priority": "low"},
        ]

        created_cases = []
        for case_data in cases_data:
            case_request = CaseRequest(**case_data, client_id="test_client", assigned_lawyer="test_lawyer")
            response = await case_agent.acreate_case(case_request, "test_user")
            created_cases.append(response.case_id)

        # Поиск по типу дела
        search_response = await case_agent.asearch_cases(
            filters={"case_type": "contract_dispute"},
            user_id="test_user"
        )

        assert_helper.assert_equal(len(search_response.results), 2, "Should find 2 contract disputes")

        # Поиск по приоритету
        priority_search = await case_agent.asearch_cases(
            filters={"priority": "high"},
            user_id="test_user"
        )

        assert_helper.assert_greater_equal(len(priority_search.results), 1, "Should find at least 1 high priority case")


class WriterAgentTests:
    """Тесты для WriterAgent."""

    @test_case("writer_agent_document_generation", TestType.FUNCTIONAL, TestSeverity.HIGH)
    async def test_document_generation(self, assert_helper: TestAssertion):
        """Тест генерации документов."""
        memory_manager = MemoryManager()
        writer_agent = WriterAgent(memory_manager=memory_manager)

        doc_request = DocumentRequest(
            document_type="letter",
            template="business_letter",
            variables={
                "recipient_name": "John Doe",
                "sender_name": "Jane Smith",
                "subject": "Legal Notice",
                "content": "This is a test legal notice."
            },
            language="english",
            tone="formal"
        )

        response = await writer_agent.agenerate_letter(doc_request, "test_user")

        assert_helper.assert_not_none(response, "Document generation response should not be None")
        assert_helper.assert_equal(response.success, True, "Document generation should succeed")
        assert_helper.assert_not_none(response.generated_document, "Generated document should not be None")
        assert_helper.assert_in("John Doe", response.generated_document.content, "Should contain recipient name")

    @test_case("writer_agent_template_processing", TestType.UNIT, TestSeverity.MEDIUM)
    async def test_template_processing(self, assert_helper: TestAssertion):
        """Тест обработки шаблонов."""
        memory_manager = MemoryManager()
        writer_agent = WriterAgent(memory_manager=memory_manager)

        # Тест замены переменных
        template_content = "Dear {{recipient_name}}, this is a {{document_type}} regarding {{subject}}."
        variables = {
            "recipient_name": "Mr. Smith",
            "document_type": "formal letter",
            "subject": "contract review"
        }

        processed = await writer_agent._substitute_variables(template_content, variables)

        assert_helper.assert_in("Mr. Smith", processed, "Should substitute recipient name")
        assert_helper.assert_in("formal letter", processed, "Should substitute document type")
        assert_helper.assert_in("contract review", processed, "Should substitute subject")
        assert_helper.assert_not_in("{{", processed, "Should not contain template markers")

    @performance_test("writer_agent_generation_performance", max_duration_ms=500, iterations=20)
    async def test_generation_performance(self):
        """Performance тест генерации документов."""
        memory_manager = MemoryManager()
        writer_agent = WriterAgent(memory_manager=memory_manager)

        doc_request = DocumentRequest(
            document_type="letter",
            template="business_letter",
            variables={"recipient_name": "Test", "content": "Test content"},
            language="english"
        )

        await writer_agent.agenerate_letter(doc_request, "test_user")


class ValidatorAgentTests:
    """Тесты для ValidatorAgent."""

    @test_case("validator_agent_rule_validation", TestType.FUNCTIONAL, TestSeverity.HIGH)
    async def test_rule_validation(self, assert_helper: TestAssertion):
        """Тест валидации по правилам."""
        memory_manager = MemoryManager()
        validator = ValidatorAgent(memory_manager=memory_manager)

        validation_request = ValidationRequest(
            content="This is a test document with proper formatting and required fields.",
            validation_type="document",
            rules=["required_fields", "format_check", "length_check"],
            context={"document_type": "contract", "min_length": 10}
        )

        response = await validator.avalidate(validation_request, "test_user")

        assert_helper.assert_not_none(response, "Validation response should not be None")
        assert_helper.assert_equal(response.success, True, "Validation should succeed")
        assert_helper.assert_greater(response.confidence_score, 0.5, "Should have reasonable confidence")

    @test_case("validator_agent_self_correction", TestType.INTEGRATION, TestSeverity.MEDIUM)
    async def test_self_correction(self, assert_helper: TestAssertion):
        """Тест самокоррекции."""
        memory_manager = MemoryManager()
        validator = ValidatorAgent(memory_manager=memory_manager)

        # Контент с проблемами для коррекции
        problematic_content = "this is a test document without proper capitalization"

        validation_request = ValidationRequest(
            content=problematic_content,
            validation_type="document",
            rules=["capitalization", "formatting"],
            auto_correct=True
        )

        response = await validator.avalidate(validation_request, "test_user")

        assert_helper.assert_not_none(response.corrected_content, "Should provide corrected content")
        assert_helper.assert_not_equal(response.corrected_content, problematic_content, "Corrected content should be different")


class RAGPipelineAgentTests:
    """Тесты для RAGPipelineAgent."""

    @test_case("rag_agent_search_functionality", TestType.FUNCTIONAL, TestSeverity.HIGH)
    async def test_search_functionality(self, assert_helper: TestAssertion):
        """Тест функциональности поиска."""
        memory_manager = MemoryManager()
        rag_agent = RAGPipelineAgent(memory_manager=memory_manager)

        search_query = SearchQuery(
            query_text="legal contract terms",
            strategy="hybrid",
            limit=5
        )

        response = await rag_agent.asearch(search_query, "test_user")

        assert_helper.assert_not_none(response, "Search response should not be None")
        assert_helper.assert_equal(response.success, True, "Search should succeed")
        assert_helper.assert_not_none(response.query_id, "Should have query ID")

    @test_case("rag_agent_document_processing", TestType.INTEGRATION, TestSeverity.MEDIUM)
    async def test_document_processing(self, assert_helper: TestAssertion):
        """Тест обработки документов."""
        memory_manager = MemoryManager()
        rag_agent = RAGPipelineAgent(memory_manager=memory_manager)

        # Тест определения типа документа
        doc_type_pdf = await rag_agent._detect_document_type("test_contract.pdf")
        doc_type_docx = await rag_agent._detect_document_type("test_document.docx")

        assert_helper.assert_equal(doc_type_pdf.value, "pdf", "Should detect PDF type")
        assert_helper.assert_equal(doc_type_docx.value, "docx", "Should detect DOCX type")

    @performance_test("rag_agent_search_performance", max_duration_ms=200, iterations=30)
    async def test_search_performance(self):
        """Performance тест поиска."""
        memory_manager = MemoryManager()
        rag_agent = RAGPipelineAgent(memory_manager=memory_manager)

        search_query = SearchQuery(
            query_text="test search query",
            limit=3
        )

        await rag_agent.asearch(search_query, "test_user")


class IntegrationTests:
    """Интеграционные тесты для взаимодействия агентов."""

    @test_case("agent_coordination_workflow", TestType.INTEGRATION, TestSeverity.CRITICAL)
    async def test_agent_coordination_workflow(self, assert_helper: TestAssertion):
        """Тест координации между агентами."""
        memory_manager = MemoryManager()

        # Инициализируем агентов
        mega_agent = MegaAgent(memory_manager=memory_manager)
        case_agent = CaseAgent(memory_manager=memory_manager)
        writer_agent = WriterAgent(memory_manager=memory_manager)

        # Создаем дело через MegaAgent
        case_command = MegaAgentCommand(
            command="/create_case",
            args=["Contract Dispute", "High priority contract issue"],
            user_id="test_user"
        )

        response = await mega_agent.handle_command(case_command, UserRole.LAWYER)

        assert_helper.assert_equal(response.success, True, "Case creation through MegaAgent should succeed")

        # Проверяем, что дело создалось
        # В реальной реализации здесь была бы более сложная логика координации

    @test_case("memory_persistence_across_agents", TestType.INTEGRATION, TestSeverity.HIGH)
    async def test_memory_persistence_across_agents(self, assert_helper: TestAssertion):
        """Тест персистентности памяти между агентами."""
        memory_manager = MemoryManager()

        # Агент A записывает в память
        case_agent = CaseAgent(memory_manager=memory_manager)
        case_request = CaseRequest(
            title="Shared Memory Test",
            description="Test case for memory sharing",
            case_type="test",
            client_id="test_client",
            assigned_lawyer="test_lawyer"
        )

        create_response = await case_agent.acreate_case(case_request, "test_user")
        assert_helper.assert_equal(create_response.success, True, "Case creation should succeed")

        # Агент B должен иметь доступ к той же памяти
        rag_agent = RAGPipelineAgent(memory_manager=memory_manager)
        search_query = SearchQuery(query_text="Shared Memory Test", limit=5)
        search_response = await rag_agent.asearch(search_query, "test_user")

        # Проверяем, что память общая (базовая проверка)
        assert_helper.assert_not_none(search_response, "Search should work with shared memory")


# Utility функции для создания test suites

def get_all_agent_tests() -> List[tuple]:
    """Получить все тесты агентов."""
    tests = []

    # MegaAgent tests
    mega_tests = MegaAgentTests()
    tests.extend([
        (mega_tests.test_initialization, "mega_agent_initialization", TestType.UNIT, TestSeverity.CRITICAL),
        (mega_tests.test_command_routing, "mega_agent_command_routing", TestType.INTEGRATION, TestSeverity.HIGH),
        (mega_tests.test_rbac_enforcement, "mega_agent_rbac_enforcement", TestType.SECURITY, TestSeverity.CRITICAL),
    ])

    # SupervisorAgent tests
    supervisor_tests = SupervisorAgentTests()
    tests.extend([
        (supervisor_tests.test_initialization, "supervisor_agent_initialization", TestType.UNIT, TestSeverity.CRITICAL),
        (supervisor_tests.test_task_analysis, "supervisor_task_analysis", TestType.INTEGRATION, TestSeverity.HIGH),
        (supervisor_tests.test_multi_agent_coordination, "supervisor_multi_agent_coordination", TestType.INTEGRATION, TestSeverity.HIGH),
    ])

    # CaseAgent tests
    case_tests = CaseAgentTests()
    tests.extend([
        (case_tests.test_crud_operations, "case_agent_crud_operations", TestType.FUNCTIONAL, TestSeverity.HIGH),
        (case_tests.test_search_functionality, "case_agent_search_functionality", TestType.FUNCTIONAL, TestSeverity.MEDIUM),
    ])

    # WriterAgent tests
    writer_tests = WriterAgentTests()
    tests.extend([
        (writer_tests.test_document_generation, "writer_agent_document_generation", TestType.FUNCTIONAL, TestSeverity.HIGH),
        (writer_tests.test_template_processing, "writer_agent_template_processing", TestType.UNIT, TestSeverity.MEDIUM),
    ])

    # ValidatorAgent tests
    validator_tests = ValidatorAgentTests()
    tests.extend([
        (validator_tests.test_rule_validation, "validator_agent_rule_validation", TestType.FUNCTIONAL, TestSeverity.HIGH),
        (validator_tests.test_self_correction, "validator_agent_self_correction", TestType.INTEGRATION, TestSeverity.MEDIUM),
    ])

    # RAGPipelineAgent tests
    rag_tests = RAGPipelineAgentTests()
    tests.extend([
        (rag_tests.test_search_functionality, "rag_agent_search_functionality", TestType.FUNCTIONAL, TestSeverity.HIGH),
        (rag_tests.test_document_processing, "rag_agent_document_processing", TestType.INTEGRATION, TestSeverity.MEDIUM),
    ])

    # Integration tests
    integration_tests = IntegrationTests()
    tests.extend([
        (integration_tests.test_agent_coordination_workflow, "agent_coordination_workflow", TestType.INTEGRATION, TestSeverity.CRITICAL),
        (integration_tests.test_memory_persistence_across_agents, "memory_persistence_across_agents", TestType.INTEGRATION, TestSeverity.HIGH),
    ])

    return tests


def get_performance_tests() -> List[tuple]:
    """Получить performance тесты."""
    tests = []

    mega_tests = MegaAgentTests()
    writer_tests = WriterAgentTests()
    rag_tests = RAGPipelineAgentTests()

    tests.extend([
        (mega_tests.test_command_performance, "mega_agent_command_performance", TestType.PERFORMANCE, TestSeverity.HIGH),
        (writer_tests.test_generation_performance, "writer_agent_generation_performance", TestType.PERFORMANCE, TestSeverity.HIGH),
        (rag_tests.test_search_performance, "rag_agent_search_performance", TestType.PERFORMANCE, TestSeverity.HIGH),
    ])

    return tests