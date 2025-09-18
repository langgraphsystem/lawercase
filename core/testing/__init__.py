"""
Testing & Quality Framework для mega_agent_pro.

Provides comprehensive testing capabilities:
- Unit testing для всех агентов и компонентов
- Integration testing для multi-agent workflows
- Performance testing и benchmarking
- Quality gates и automated quality control
- Mock services для external dependencies
- Test data generation и fixtures
- Continuous testing integration
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    # Core Testing Framework
    "TestRunner",
    "TestResult",
    "TestSuite",
    "TestAssertion",
    "TestStatus",
    "TestType",
    "TestSeverity",
    "QualityGates",

    # Mock Services
    "MockService",
    "MockLLMService",
    "MockDatabaseService",

    # Test Decorators
    "test_case",
    "performance_test",
    "skip_test",

    # Agent Tests
    "get_all_agent_tests",
    "get_performance_tests",

    # Utilities
    "create_test_runner",
]

# Import core testing framework
from .test_framework import (
    TestRunner,
    TestResult,
    TestSuite,
    TestAssertion,
    TestStatus,
    TestType,
    TestSeverity,
    QualityGates,
    MockService,
    MockLLMService,
    MockDatabaseService,
    test_case,
    performance_test,
    skip_test,
    create_test_runner,
)

# Import agent tests
from .agent_tests import (
    get_all_agent_tests,
    get_performance_tests,
)