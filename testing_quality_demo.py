#!/usr/bin/env python3
"""
Testing & Quality Framework Demo для mega_agent_pro.

Демонстрирует:
1. Unit testing для всех агентов
2. Integration testing для multi-agent workflows
3. Performance testing и benchmarking
4. Quality gates и automated quality control
5. Mock services для external dependencies
6. Comprehensive test reporting
7. Continuous quality monitoring

Запуск:
    python testing_quality_demo.py
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.testing import (
    TestType,
    TestSeverity,
    QualityGates,
    create_test_runner,
    get_all_agent_tests,
    get_performance_tests,
)


async def demo_basic_testing():
    """Демонстрация базового тестирования."""
    print("🧪 === Basic Testing Demo ===\n")

    runner = await create_test_runner()

    # Простой unit тест
    async def sample_unit_test(assert_helper):
        """Пример unit теста."""
        result = 2 + 2
        assert_helper.assert_equal(result, 4, "Basic math should work")
        assert_helper.assert_not_equal(result, 5, "2+2 should not equal 5")
        assert_helper.assert_greater(result, 3, "Result should be greater than 3")

    # Запускаем тест
    test_result = await runner.run_test(
        sample_unit_test,
        "basic_math_test",
        TestType.UNIT,
        TestSeverity.LOW
    )

    print(f"📋 Test: {test_result.test_name}")
    print(f"   📊 Status: {test_result.status.value}")
    print(f"   ⏱️ Duration: {test_result.duration_ms:.2f}ms")
    print(f"   ✅ Assertions passed: {test_result.assertions_passed}/{test_result.assertions_count}")
    print(f"   📈 Success rate: {test_result.success_rate:.1f}%")

    if test_result.output:
        print(f"   📝 Output: {test_result.output}")

    print()


async def demo_mock_services():
    """Демонстрация mock сервисов."""
    print("🎭 === Mock Services Demo ===\n")

    runner = await create_test_runner()

    # Тест с LLM mock сервисом
    async def test_llm_mock(assert_helper):
        """Тест mock LLM сервиса."""
        llm_service = runner.get_mock_service("llm")
        assert_helper.assert_not_none(llm_service, "LLM service should be available")

        # Тестируем генерацию ответа
        response = await llm_service.generate_response("Hello, how are you?")
        assert_helper.assert_not_none(response, "Should generate response")
        assert_helper.assert_in("help", response.lower(), "Response should be helpful")

        # Проверяем счетчик вызовов
        assert_helper.assert_equal(llm_service.call_count, 1, "Should track call count")

    # Тест с Database mock сервисом
    async def test_database_mock(assert_helper):
        """Тест mock Database сервиса."""
        db_service = runner.get_mock_service("database")
        assert_helper.assert_not_none(db_service, "Database service should be available")

        # Тестируем запрос пользователей
        users = await db_service.query("users")
        assert_helper.assert_greater(len(users), 0, "Should have test users")

        # Тестируем фильтрацию
        admins = await db_service.query("users", {"role": "admin"})
        assert_helper.assert_equal(len(admins), 1, "Should find one admin")
        assert_helper.assert_equal(admins[0]["username"], "admin", "Admin username should match")

    # Запускаем тесты
    llm_result = await runner.run_test(test_llm_mock, "llm_mock_test", TestType.UNIT, TestSeverity.MEDIUM)
    db_result = await runner.run_test(test_database_mock, "database_mock_test", TestType.UNIT, TestSeverity.MEDIUM)

    print("🎭 Mock service test results:")
    for result in [llm_result, db_result]:
        status_icon = "✅" if result.status.value == "passed" else "❌"
        print(f"   {status_icon} {result.test_name}: {result.status.value} ({result.duration_ms:.1f}ms)")

    print()


async def demo_agent_testing():
    """Демонстрация тестирования агентов."""
    print("🤖 === Agent Testing Demo ===\n")

    runner = await create_test_runner()

    # Получаем subset агентских тестов для демонстрации
    all_tests = get_all_agent_tests()
    demo_tests = all_tests[:5]  # Берем первые 5 тестов

    print(f"🔬 Running {len(demo_tests)} agent tests...")

    test_suite = await runner.run_test_suite(
        "agent_demo_suite",
        demo_tests,
        "Demonstration of agent testing capabilities"
    )

    print(f"\n📊 Test Suite Results: {test_suite.name}")
    print(f"   ⏱️ Duration: {test_suite.duration_ms:.1f}ms")
    print(f"   📈 Success rate: {test_suite.success_rate:.1f}%")
    print(f"   ✅ Passed: {test_suite.passed_tests}/{test_suite.total_tests}")

    print("\n📋 Individual test results:")
    for test in test_suite.tests:
        status_icon = "✅" if test.status.value == "passed" else "❌" if test.status.value == "failed" else "⚠️"
        print(f"   {status_icon} {test.test_name}")
        print(f"      🎯 Type: {test.test_type.value}, Severity: {test.severity.value}")
        print(f"      ⏱️ Duration: {test.duration_ms:.1f}ms")

        if test.assertions_count > 0:
            print(f"      ✅ Assertions: {test.assertions_passed}/{test.assertions_count}")

        if test.status.value == "failed" and test.error_message:
            print(f"      ❌ Error: {test.error_message}")

    print()


async def demo_performance_testing():
    """Демонстрация performance тестирования."""
    print("⚡ === Performance Testing Demo ===\n")

    runner = await create_test_runner()

    # Простой performance тест
    async def simple_performance_test():
        """Простая операция для performance теста."""
        # Симуляция работы
        await asyncio.sleep(0.001)  # 1ms
        return sum(range(100))

    # Запускаем performance тест
    perf_result = await runner.run_performance_test(
        simple_performance_test,
        "simple_operation_performance",
        iterations=50,
        max_duration_ms=10
    )

    print(f"⚡ Performance Test: {perf_result.test_name}")
    print(f"   📊 Status: {perf_result.status.value}")
    print(f"   ⏱️ Total Duration: {perf_result.duration_ms:.1f}ms")

    if perf_result.metadata:
        metadata = perf_result.metadata
        print(f"   🔄 Iterations: {metadata['iterations']}")
        print(f"   📊 Average: {metadata['avg_duration_ms']:.2f}ms")
        print(f"   📈 Max: {metadata['max_duration_ms']:.2f}ms")
        print(f"   📉 Min: {metadata['min_duration_ms']:.2f}ms")
        print(f"   🎯 Target: < {metadata['target_max_ms']:.1f}ms")

    # Получаем реальные performance тесты агентов
    perf_tests = get_performance_tests()
    if perf_tests:
        print(f"\n🚀 Running agent performance tests ({len(perf_tests)} tests)...")

        perf_suite = await runner.run_test_suite(
            "performance_suite",
            perf_tests[:2],  # Берем первые 2 для демонстрации
            "Agent performance testing"
        )

        print("\n📊 Performance Suite Results:")
        print(f"   ⏱️ Total Duration: {perf_suite.duration_ms:.1f}ms")
        print(f"   ✅ Passed: {perf_suite.passed_tests}/{perf_suite.total_tests}")

        for test in perf_suite.tests:
            if test.test_type == TestType.PERFORMANCE:
                status_icon = "✅" if test.status.value == "passed" else "❌"
                avg_time = test.metadata.get('avg_duration_ms', 0) if test.metadata else 0
                print(f"   {status_icon} {test.test_name}: {avg_time:.2f}ms avg")

    print()


async def demo_quality_gates():
    """Демонстрация quality gates."""
    print("🚧 === Quality Gates Demo ===\n")

    runner = await create_test_runner()

    # Создаем набор тестов с разными уровнями критичности
    test_functions = [
        # Критические тесты
        (lambda assert_helper: assert_helper.assert_true(True, "Critical test 1"), "critical_test_1", TestType.UNIT, TestSeverity.CRITICAL),
        (lambda assert_helper: assert_helper.assert_true(True, "Critical test 2"), "critical_test_2", TestType.SECURITY, TestSeverity.CRITICAL),

        # Высокоприоритетные тесты
        (lambda assert_helper: assert_helper.assert_equal(2+2, 4, "High priority test"), "high_priority_test", TestType.FUNCTIONAL, TestSeverity.HIGH),

        # Средние тесты
        (lambda assert_helper: assert_helper.assert_not_none("test", "Medium test"), "medium_test", TestType.INTEGRATION, TestSeverity.MEDIUM),

        # Один тест, который может провалиться
        (lambda assert_helper: assert_helper.assert_equal(1, 1, "Sometimes failing test"), "variable_test", TestType.UNIT, TestSeverity.LOW),
    ]

    # Запускаем test suite
    quality_suite = await runner.run_test_suite(
        "quality_gates_suite",
        test_functions,
        "Quality gates demonstration"
    )

    print(f"📊 Quality Suite: {quality_suite.name}")
    print(f"   ✅ Passed: {quality_suite.passed_tests}/{quality_suite.total_tests}")
    print(f"   📈 Success Rate: {quality_suite.success_rate:.1f}%")

    # Оцениваем quality gates
    print("\n🚧 Quality Gates Evaluation:")
    gates = QualityGates.evaluate_quality_gates([quality_suite])

    print(f"   🎯 Test Coverage: {'✅ PASS' if gates['test_coverage']['passed'] else '❌ FAIL'}")
    for detail in gates['test_coverage']['details']:
        print(f"      📦 {detail['suite']}: {detail['success_rate']:.1f}%")

    print(f"   ⚡ Performance: {'✅ PASS' if gates['performance']['passed'] else '❌ FAIL'}")

    print(f"   🔴 Critical Tests: {'✅ PASS' if gates['critical_tests']['passed'] else '❌ FAIL'}")
    for detail in gates['critical_tests']['details']:
        status_icon = "✅" if detail['passed'] else "❌"
        print(f"      {status_icon} {detail['test']}")

    print(f"\n🏆 Overall Quality: {'✅ PASS' if gates['overall']['passed'] else '❌ FAIL'}")
    print(f"   📊 Success Rate: {gates['overall']['success_rate']:.1f}%")
    print(f"   📈 Total Tests: {gates['overall']['total_tests']}")

    print()


async def demo_comprehensive_reporting():
    """Демонстрация комплексной отчетности."""
    print("📋 === Comprehensive Reporting Demo ===\n")

    runner = await create_test_runner()

    # Запускаем несколько test suites
    print("🔄 Running multiple test suites...")

    # Unit tests suite
    unit_tests = [
        (lambda assert_helper: assert_helper.assert_true(True), "unit_test_1", TestType.UNIT, TestSeverity.HIGH),
        (lambda assert_helper: assert_helper.assert_equal(5, 5), "unit_test_2", TestType.UNIT, TestSeverity.MEDIUM),
        (lambda assert_helper: assert_helper.assert_not_none("hello"), "unit_test_3", TestType.UNIT, TestSeverity.LOW),
    ]

    unit_suite = await runner.run_test_suite("unit_tests", unit_tests, "Unit testing suite")

    # Integration tests suite
    integration_tests = [
        (lambda assert_helper: assert_helper.assert_in("test", "testing"), "integration_test_1", TestType.INTEGRATION, TestSeverity.HIGH),
        (lambda assert_helper: assert_helper.assert_greater(10, 5), "integration_test_2", TestType.INTEGRATION, TestSeverity.MEDIUM),
    ]

    integration_suite = await runner.run_test_suite("integration_tests", integration_tests, "Integration testing suite")

    # Performance test
    async def perf_operation():
        await asyncio.sleep(0.001)

    perf_result = await runner.run_performance_test(perf_operation, "demo_performance", iterations=20, max_duration_ms=5)

    # Генерируем comprehensive отчет
    print("\n📊 Generating comprehensive report...")

    # Text report
    text_report = runner.generate_report("text")
    print("\n" + "="*50)
    print("TEXT REPORT:")
    print("="*50)
    print(text_report)

    # JSON report (краткая версия для демо)
    json_report = runner.generate_report("json")
    print("\n" + "="*50)
    print("JSON REPORT GENERATED:")
    print("="*50)
    print("✅ JSON report generated successfully")
    print(f"📊 Report size: {len(json_report)} characters")
    print("📄 Contains: test suites, results, metrics, and timestamps")

    print()


async def demo_continuous_quality_monitoring():
    """Демонстрация непрерывного мониторинга качества."""
    print("📡 === Continuous Quality Monitoring Demo ===\n")

    runner = await create_test_runner()

    print("🔄 Simulating continuous testing workflow...")

    # Симуляция нескольких циклов тестирования
    quality_trends = []

    for cycle in range(3):
        print(f"\n🔄 Test Cycle {cycle + 1}:")

        # Варьируем количество тестов и их успешность
        test_count = 3 + cycle
        success_rate = 100 - (cycle * 10)  # Ухудшаем на каждом цикле для демонстрации

        cycle_tests = []
        for i in range(test_count):
            # Симулируем разную успешность
            should_pass = i < (test_count * success_rate / 100)

            test_func = (
                lambda assert_helper, should_pass=should_pass:
                assert_helper.assert_true(should_pass, f"Cycle test {i}")
            )

            cycle_tests.append((test_func, f"cycle_{cycle}_test_{i}", TestType.FUNCTIONAL, TestSeverity.MEDIUM))

        # Запускаем тесты цикла
        cycle_suite = await runner.run_test_suite(f"cycle_{cycle}", cycle_tests, f"Test cycle {cycle + 1}")

        # Оцениваем качество
        gates = QualityGates.evaluate_quality_gates([cycle_suite])

        quality_trend = {
            "cycle": cycle + 1,
            "success_rate": cycle_suite.success_rate,
            "total_tests": cycle_suite.total_tests,
            "duration_ms": cycle_suite.duration_ms,
            "quality_gates_passed": gates['overall']['passed']
        }

        quality_trends.append(quality_trend)

        print(f"   📊 Success Rate: {quality_trend['success_rate']:.1f}%")
        print(f"   ⏱️ Duration: {quality_trend['duration_ms']:.1f}ms")
        print(f"   🚧 Quality Gates: {'✅ PASS' if quality_trend['quality_gates_passed'] else '❌ FAIL'}")

        # Симуляция задержки между циклами
        await asyncio.sleep(0.1)

    # Анализ трендов качества
    print("\n📈 Quality Trends Analysis:")
    print(f"   📊 Average Success Rate: {sum(t['success_rate'] for t in quality_trends) / len(quality_trends):.1f}%")
    print(f"   ⏱️ Average Duration: {sum(t['duration_ms'] for t in quality_trends) / len(quality_trends):.1f}ms")

    improving_cycles = sum(1 for i in range(1, len(quality_trends))
                          if quality_trends[i]['success_rate'] > quality_trends[i-1]['success_rate'])

    print(f"   📈 Improving Cycles: {improving_cycles}/{len(quality_trends)-1}")

    if quality_trends[-1]['success_rate'] < quality_trends[0]['success_rate']:
        print("   ⚠️ Quality degradation detected!")
        print("   💡 Recommendations:")
        print("      - Increase test coverage")
        print("      - Review recent code changes")
        print("      - Add more integration tests")
    else:
        print("   ✅ Quality is stable or improving")

    print()


async def main():
    """Главная функция демонстрации."""
    print("🧪 MEGA AGENT PRO - Testing & Quality Framework Demo")
    print("=" * 70)
    print()

    try:
        # Демонстрируем различные аспекты тестирования
        await demo_basic_testing()
        await demo_mock_services()
        await demo_agent_testing()
        await demo_performance_testing()
        await demo_quality_gates()
        await demo_comprehensive_reporting()
        await demo_continuous_quality_monitoring()

        print("✅ === Testing & Quality Demo Complete ===")
        print()
        print("🎯 Key Features Demonstrated:")
        print("   ✅ Comprehensive unit and integration testing")
        print("   ✅ Mock services for isolated testing")
        print("   ✅ Performance testing with benchmarking")
        print("   ✅ Quality gates for automated quality control")
        print("   ✅ Detailed test reporting (text and JSON)")
        print("   ✅ Continuous quality monitoring")
        print("   ✅ Agent-specific testing capabilities")
        print("   ✅ RBAC and security testing")
        print()
        print("🚀 Quality Benefits:")
        print("   📈 Automated quality assurance")
        print("   🔍 Early bug detection and prevention")
        print("   ⚡ Performance regression detection")
        print("   🛡️ Security vulnerability testing")
        print("   📊 Comprehensive quality metrics")
        print("   🔄 Continuous improvement feedback")
        print()
        print("🔧 Next Steps:")
        print("   1. Integrate with CI/CD pipelines")
        print("   2. Add test coverage analysis")
        print("   3. Implement automated test generation")
        print("   4. Create quality dashboards")
        print("   5. Add chaos engineering tests")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())