"""
Comprehensive Testing & Quality Framework для mega_agent_pro.

Обеспечивает:
- Unit testing для всех агентов и компонентов
- Integration testing для multi-agent workflows
- Performance testing и benchmarking
- Quality gates и code coverage
- Automated testing pipelines
- Mock services для external dependencies
- Test data generation и fixtures
- Continuous quality monitoring
"""

from __future__ import annotations

import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field


class TestStatus(str, Enum):
    """Статусы тестов."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestType(str, Enum):
    """Типы тестов."""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    FUNCTIONAL = "functional"
    SMOKE = "smoke"
    LOAD = "load"
    STRESS = "stress"


class TestSeverity(str, Enum):
    """Уровни серьезности тестов."""
    CRITICAL = "critical"      # Must pass for production
    HIGH = "high"             # Important functionality
    MEDIUM = "medium"         # Standard functionality
    LOW = "low"               # Nice to have
    INFO = "info"             # Informational


class TestResult(BaseModel):
    """Результат выполнения теста."""
    test_id: str = Field(..., description="ID теста")
    test_name: str = Field(..., description="Название теста")
    test_type: TestType = Field(..., description="Тип теста")
    status: TestStatus = Field(..., description="Статус теста")
    severity: TestSeverity = Field(TestSeverity.MEDIUM, description="Серьезность")
    duration_ms: float = Field(0, description="Время выполнения в миллисекундах")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(None, description="Время завершения")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    error_traceback: Optional[str] = Field(None, description="Traceback ошибки")
    assertions_count: int = Field(0, description="Количество проверок")
    assertions_passed: int = Field(0, description="Пройденные проверки")
    output: Optional[str] = Field(None, description="Вывод теста")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")

    @property
    def success_rate(self) -> float:
        """Процент успешных assertions."""
        if self.assertions_count == 0:
            return 100.0 if self.status == TestStatus.PASSED else 0.0
        return (self.assertions_passed / self.assertions_count) * 100


class TestSuite(BaseModel):
    """Набор тестов."""
    suite_id: str = Field(..., description="ID набора тестов")
    name: str = Field(..., description="Название набора")
    description: Optional[str] = Field(None, description="Описание набора")
    tests: List[TestResult] = Field(default_factory=list, description="Результаты тестов")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(None, description="Время завершения")

    @property
    def duration_ms(self) -> float:
        """Общее время выполнения набора."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0

    @property
    def total_tests(self) -> int:
        """Общее количество тестов."""
        return len(self.tests)

    @property
    def passed_tests(self) -> int:
        """Количество пройденных тестов."""
        return len([t for t in self.tests if t.status == TestStatus.PASSED])

    @property
    def failed_tests(self) -> int:
        """Количество проваленных тестов."""
        return len([t for t in self.tests if t.status == TestStatus.FAILED])

    @property
    def success_rate(self) -> float:
        """Процент успешных тестов."""
        if self.total_tests == 0:
            return 100.0
        return (self.passed_tests / self.total_tests) * 100


class MockService(ABC):
    """Абстрактный базовый класс для mock сервисов."""

    @abstractmethod
    async def setup(self) -> None:
        """Настройка mock сервиса."""
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """Очистка mock сервиса."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Сброс состояния mock сервиса."""
        pass


class MockLLMService(MockService):
    """Mock сервис для LLM API."""

    def __init__(self):
        self.responses: Dict[str, str] = {}
        self.call_count: int = 0
        self.delay_ms: int = 100

    async def setup(self) -> None:
        """Настройка mock LLM сервиса."""
        self.responses = {
            "hello": "Hello! How can I help you?",
            "legal": "This is a legal matter that requires careful consideration.",
            "contract": "The contract appears to be valid and enforceable.",
            "default": "I understand your question. Let me help you with that."
        }

    async def teardown(self) -> None:
        """Очистка mock LLM сервиса."""
        self.responses.clear()
        self.call_count = 0

    async def reset(self) -> None:
        """Сброс счетчика вызовов."""
        self.call_count = 0

    async def generate_response(self, prompt: str) -> str:
        """Генерация mock ответа."""
        await asyncio.sleep(self.delay_ms / 1000)  # Симуляция задержки API
        self.call_count += 1

        # Поиск подходящего ответа
        for keyword, response in self.responses.items():
            if keyword.lower() in prompt.lower():
                return response

        return self.responses["default"]


class MockDatabaseService(MockService):
    """Mock сервис для базы данных."""

    def __init__(self):
        self.data: Dict[str, List[Dict[str, Any]]] = {}
        self.query_count: int = 0

    async def setup(self) -> None:
        """Настройка mock базы данных."""
        self.data = {
            "users": [
                {"id": 1, "username": "admin", "role": "admin"},
                {"id": 2, "username": "lawyer", "role": "lawyer"},
                {"id": 3, "username": "client", "role": "client"},
            ],
            "cases": [
                {"id": 1, "title": "Contract Dispute", "status": "open", "lawyer_id": 2},
                {"id": 2, "title": "Employment Issue", "status": "closed", "lawyer_id": 2},
            ],
            "documents": [
                {"id": 1, "name": "contract.pdf", "case_id": 1, "type": "contract"},
                {"id": 2, "name": "evidence.docx", "case_id": 1, "type": "evidence"},
            ]
        }

    async def teardown(self) -> None:
        """Очистка mock базы данных."""
        self.data.clear()
        self.query_count = 0

    async def reset(self) -> None:
        """Сброс счетчика запросов."""
        self.query_count = 0

    async def query(self, table: str, conditions: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Выполнение mock запроса."""
        await asyncio.sleep(0.01)  # Симуляция задержки БД
        self.query_count += 1

        if table not in self.data:
            return []

        results = self.data[table]

        if conditions:
            filtered_results = []
            for item in results:
                match = True
                for key, value in conditions.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                if match:
                    filtered_results.append(item)
            results = filtered_results

        return results.copy()


class TestAssertion:
    """Класс для проведения assertions в тестах."""

    def __init__(self, test_result: TestResult):
        self.test_result = test_result

    def assert_true(self, condition: bool, message: str = "Expected True") -> bool:
        """Проверка истинности."""
        self.test_result.assertions_count += 1
        if condition:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, "Expected True, got False")
            return False

    def assert_false(self, condition: bool, message: str = "Expected False") -> bool:
        """Проверка ложности."""
        self.test_result.assertions_count += 1
        if not condition:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, "Expected False, got True")
            return False

    def assert_equal(self, actual: Any, expected: Any, message: str = "Values should be equal") -> bool:
        """Проверка равенства."""
        self.test_result.assertions_count += 1
        if actual == expected:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, f"Expected {expected}, got {actual}")
            return False

    def assert_not_equal(self, actual: Any, expected: Any, message: str = "Values should not be equal") -> bool:
        """Проверка неравенства."""
        self.test_result.assertions_count += 1
        if actual != expected:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, f"Expected {actual} != {expected}")
            return False

    def assert_in(self, item: Any, container: Any, message: str = "Item should be in container") -> bool:
        """Проверка присутствия."""
        self.test_result.assertions_count += 1
        if item in container:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, f"Expected {item} in {container}")
            return False

    def assert_not_none(self, value: Any, message: str = "Value should not be None") -> bool:
        """Проверка на не-None."""
        self.test_result.assertions_count += 1
        if value is not None:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, "Expected not None, got None")
            return False

    def assert_none(self, value: Any, message: str = "Value should be None") -> bool:
        """Проверка на None."""
        self.test_result.assertions_count += 1
        if value is None:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, f"Expected None, got {value}")
            return False

    def assert_greater(self, actual: Union[int, float], expected: Union[int, float], message: str = "Value should be greater") -> bool:
        """Проверка больше."""
        self.test_result.assertions_count += 1
        if actual > expected:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, f"Expected {actual} > {expected}")
            return False

    def assert_less(self, actual: Union[int, float], expected: Union[int, float], message: str = "Value should be less") -> bool:
        """Проверка меньше."""
        self.test_result.assertions_count += 1
        if actual < expected:
            self.test_result.assertions_passed += 1
            return True
        else:
            self._log_assertion_failure(message, f"Expected {actual} < {expected}")
            return False

    def _log_assertion_failure(self, message: str, details: str) -> None:
        """Логирование неудачной проверки."""
        if self.test_result.output is None:
            self.test_result.output = ""
        self.test_result.output += f"ASSERTION FAILED: {message} - {details}\n"


class TestRunner:
    """Основной класс для запуска тестов."""

    def __init__(self):
        self.mock_services: Dict[str, MockService] = {}
        self.test_suites: List[TestSuite] = []
        self.global_setup_done: bool = False

    def add_mock_service(self, name: str, service: MockService) -> None:
        """Добавить mock сервис."""
        self.mock_services[name] = service

    async def setup_mocks(self) -> None:
        """Настройка всех mock сервисов."""
        for service in self.mock_services.values():
            await service.setup()

    async def teardown_mocks(self) -> None:
        """Очистка всех mock сервисов."""
        for service in self.mock_services.values():
            await service.teardown()

    async def reset_mocks(self) -> None:
        """Сброс состояния всех mock сервисов."""
        for service in self.mock_services.values():
            await service.reset()

    def get_mock_service(self, name: str) -> Optional[MockService]:
        """Получить mock сервис по имени."""
        return self.mock_services.get(name)

    async def run_test(self, test_func: Callable, test_name: str, test_type: TestType = TestType.UNIT,
                      severity: TestSeverity = TestSeverity.MEDIUM, **kwargs) -> TestResult:
        """Запуск одного теста."""
        test_id = f"{test_type.value}_{test_name}_{int(time.time())}"

        test_result = TestResult(
            test_id=test_id,
            test_name=test_name,
            test_type=test_type,
            status=TestStatus.RUNNING,
            severity=severity
        )

        start_time = time.time()
        test_result.start_time = datetime.utcnow()

        try:
            # Создаем assertion helper
            assertion = TestAssertion(test_result)

            # Проверяем, является ли функция асинхронной
            if asyncio.iscoroutinefunction(test_func):
                await test_func(assertion, **kwargs)
            else:
                test_func(assertion, **kwargs)

            # Определяем статус на основе assertions
            if test_result.assertions_count == 0:
                test_result.status = TestStatus.PASSED  # Нет assertions - считаем пройденным
            elif test_result.assertions_passed == test_result.assertions_count:
                test_result.status = TestStatus.PASSED
            else:
                test_result.status = TestStatus.FAILED

        except Exception as e:
            test_result.status = TestStatus.ERROR
            test_result.error_message = str(e)
            test_result.error_traceback = traceback.format_exc()

        finally:
            end_time = time.time()
            test_result.end_time = datetime.utcnow()
            test_result.duration_ms = (end_time - start_time) * 1000

        return test_result

    async def run_test_suite(self, suite_name: str, test_functions: List[Tuple[Callable, str, TestType, TestSeverity]],
                           description: Optional[str] = None) -> TestSuite:
        """Запуск набора тестов."""
        suite_id = f"suite_{suite_name}_{int(time.time())}"

        test_suite = TestSuite(
            suite_id=suite_id,
            name=suite_name,
            description=description
        )

        # Сброс состояния mock сервисов перед запуском набора
        await self.reset_mocks()

        for test_func, test_name, test_type, severity in test_functions:
            test_result = await self.run_test(test_func, test_name, test_type, severity)
            test_suite.tests.append(test_result)

        test_suite.end_time = datetime.utcnow()
        self.test_suites.append(test_suite)

        return test_suite

    async def run_performance_test(self, test_func: Callable, test_name: str,
                                 iterations: int = 100, max_duration_ms: float = 1000) -> TestResult:
        """Запуск performance теста."""
        test_result = TestResult(
            test_id=f"perf_{test_name}_{int(time.time())}",
            test_name=test_name,
            test_type=TestType.PERFORMANCE,
            status=TestStatus.RUNNING,
            severity=TestSeverity.HIGH
        )

        start_time = time.time()
        test_result.start_time = datetime.utcnow()

        try:
            durations = []

            for i in range(iterations):
                iter_start = time.time()

                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()

                iter_end = time.time()
                iteration_duration = (iter_end - iter_start) * 1000
                durations.append(iteration_duration)

            # Анализируем результаты
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)

            assertion = TestAssertion(test_result)
            assertion.assert_less(avg_duration, max_duration_ms,
                                f"Average duration should be less than {max_duration_ms}ms")

            test_result.metadata = {
                "iterations": iterations,
                "avg_duration_ms": avg_duration,
                "max_duration_ms": max_duration,
                "min_duration_ms": min_duration,
                "total_duration_ms": sum(durations),
                "target_max_ms": max_duration_ms
            }

            test_result.output = f"Performance test completed: {iterations} iterations, avg: {avg_duration:.2f}ms"

            if test_result.assertions_passed == test_result.assertions_count:
                test_result.status = TestStatus.PASSED
            else:
                test_result.status = TestStatus.FAILED

        except Exception as e:
            test_result.status = TestStatus.ERROR
            test_result.error_message = str(e)
            test_result.error_traceback = traceback.format_exc()

        finally:
            end_time = time.time()
            test_result.end_time = datetime.utcnow()
            test_result.duration_ms = (end_time - start_time) * 1000

        return test_result

    def generate_report(self, format: str = "text") -> str:
        """Генерация отчета о тестах."""
        if format == "text":
            return self._generate_text_report()
        elif format == "json":
            return self._generate_json_report()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_text_report(self) -> str:
        """Генерация текстового отчета."""
        report = []
        report.append("=" * 80)
        report.append("MEGA AGENT PRO - TEST EXECUTION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")

        total_suites = len(self.test_suites)
        total_tests = sum(suite.total_tests for suite in self.test_suites)
        total_passed = sum(suite.passed_tests for suite in self.test_suites)
        total_failed = sum(suite.failed_tests for suite in self.test_suites)
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 100

        report.append("SUMMARY:")
        report.append(f"  Test Suites: {total_suites}")
        report.append(f"  Total Tests: {total_tests}")
        report.append(f"  Passed: {total_passed}")
        report.append(f"  Failed: {total_failed}")
        report.append(f"  Success Rate: {overall_success_rate:.1f}%")
        report.append("")

        for suite in self.test_suites:
            report.append(f"Suite: {suite.name}")
            report.append(f"  Duration: {suite.duration_ms:.1f}ms")
            report.append(f"  Tests: {suite.total_tests} (Passed: {suite.passed_tests}, Failed: {suite.failed_tests})")
            report.append(f"  Success Rate: {suite.success_rate:.1f}%")

            for test in suite.tests:
                status_icon = "✅" if test.status == TestStatus.PASSED else "❌" if test.status == TestStatus.FAILED else "⚠️"
                report.append(f"    {status_icon} {test.test_name} ({test.test_type.value}) - {test.duration_ms:.1f}ms")

                if test.status == TestStatus.FAILED and test.error_message:
                    report.append(f"      Error: {test.error_message}")

            report.append("")

        return "\n".join(report)

    def _generate_json_report(self) -> str:
        """Генерация JSON отчета."""
        import json

        report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_suites": len(self.test_suites),
                "total_tests": sum(suite.total_tests for suite in self.test_suites),
                "total_passed": sum(suite.passed_tests for suite in self.test_suites),
                "total_failed": sum(suite.failed_tests for suite in self.test_suites),
            },
            "test_suites": [suite.dict() for suite in self.test_suites]
        }

        if report_data["summary"]["total_tests"] > 0:
            report_data["summary"]["success_rate"] = (
                report_data["summary"]["total_passed"] /
                report_data["summary"]["total_tests"] * 100
            )
        else:
            report_data["summary"]["success_rate"] = 100.0

        return json.dumps(report_data, indent=2, default=str)


class QualityGates:
    """Контроль качества и quality gates."""

    @staticmethod
    def check_test_coverage(test_suite: TestSuite, minimum_coverage: float = 80.0) -> bool:
        """Проверка покрытия тестами."""
        if test_suite.total_tests == 0:
            return False
        return test_suite.success_rate >= minimum_coverage

    @staticmethod
    def check_performance_requirements(test_results: List[TestResult], max_avg_duration_ms: float = 500) -> bool:
        """Проверка требований по производительности."""
        performance_tests = [t for t in test_results if t.test_type == TestType.PERFORMANCE]

        if not performance_tests:
            return True  # Нет performance тестов - считаем пройденным

        for test in performance_tests:
            if test.status != TestStatus.PASSED:
                return False

            if "avg_duration_ms" in test.metadata:
                if test.metadata["avg_duration_ms"] > max_avg_duration_ms:
                    return False

        return True

    @staticmethod
    def check_critical_tests(test_results: List[TestResult]) -> bool:
        """Проверка критических тестов."""
        critical_tests = [t for t in test_results if t.severity == TestSeverity.CRITICAL]

        for test in critical_tests:
            if test.status != TestStatus.PASSED:
                return False

        return True

    @staticmethod
    def evaluate_quality_gates(test_suites: List[TestSuite]) -> Dict[str, Any]:
        """Оценка всех quality gates."""
        all_tests = []
        for suite in test_suites:
            all_tests.extend(suite.tests)

        gates = {
            "test_coverage": {
                "passed": True,
                "details": []
            },
            "performance": {
                "passed": QualityGates.check_performance_requirements(all_tests),
                "details": []
            },
            "critical_tests": {
                "passed": QualityGates.check_critical_tests(all_tests),
                "details": []
            },
            "overall": {
                "passed": False,
                "success_rate": 0.0
            }
        }

        # Проверяем покрытие по сьютам
        for suite in test_suites:
            coverage_passed = QualityGates.check_test_coverage(suite)
            gates["test_coverage"]["details"].append({
                "suite": suite.name,
                "passed": coverage_passed,
                "success_rate": suite.success_rate
            })
            if not coverage_passed:
                gates["test_coverage"]["passed"] = False

        # Проверяем performance
        perf_tests = [t for t in all_tests if t.test_type == TestType.PERFORMANCE]
        for test in perf_tests:
            gates["performance"]["details"].append({
                "test": test.test_name,
                "passed": test.status == TestStatus.PASSED,
                "avg_duration_ms": test.metadata.get("avg_duration_ms", 0)
            })

        # Проверяем критические тесты
        critical_tests = [t for t in all_tests if t.severity == TestSeverity.CRITICAL]
        for test in critical_tests:
            gates["critical_tests"]["details"].append({
                "test": test.test_name,
                "passed": test.status == TestStatus.PASSED,
                "status": test.status.value
            })

        # Общая оценка
        all_gates_passed = (
            gates["test_coverage"]["passed"] and
            gates["performance"]["passed"] and
            gates["critical_tests"]["passed"]
        )

        total_tests = len(all_tests)
        passed_tests = len([t for t in all_tests if t.status == TestStatus.PASSED])

        gates["overall"] = {
            "passed": all_gates_passed,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 100.0,
            "total_tests": total_tests,
            "passed_tests": passed_tests
        }

        return gates


# Utility decorators и функции

def test_case(name: str, test_type: TestType = TestType.UNIT, severity: TestSeverity = TestSeverity.MEDIUM):
    """Декоратор для пометки функций как тестов."""
    def decorator(func):
        func._test_name = name
        func._test_type = test_type
        func._test_severity = severity
        return func
    return decorator


def performance_test(name: str, max_duration_ms: float = 1000, iterations: int = 100):
    """Декоратор для performance тестов."""
    def decorator(func):
        func._test_name = name
        func._test_type = TestType.PERFORMANCE
        func._test_severity = TestSeverity.HIGH
        func._performance_max_duration = max_duration_ms
        func._performance_iterations = iterations
        return func
    return decorator


def skip_test(reason: str):
    """Декоратор для пропуска тестов."""
    def decorator(func):
        func._skip_test = True
        func._skip_reason = reason
        return func
    return decorator


async def create_test_runner() -> TestRunner:
    """Создать настроенный TestRunner."""
    runner = TestRunner()

    # Добавляем mock сервисы
    runner.add_mock_service("llm", MockLLMService())
    runner.add_mock_service("database", MockDatabaseService())

    # Настраиваем mock сервисы
    await runner.setup_mocks()

    return runner