"""Smoke tests: verify critical modules import without errors.

These tests catch broken imports, circular dependencies, and missing
dependencies early in CI before more expensive integration tests run.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# Modules that MUST import cleanly for the system to start
CRITICAL_MODULES = [
    "core.config",
    "core.exceptions",
    "core.retry",
    "core.resilience",
    "core.logging_config",
    "core.logging_utils",
    "core.di.container",
    "core.security.config",
    "core.security.encryption",
    "core.security.audit_trail",
    "core.security.pii_detector",
    "core.security.prompt_injection_detector",
    "core.caching.multi_level_cache",
    "core.memory.agentic_memory",
    "core.memory.memory_hierarchy",
    "core.context.context_manager",
    "core.context.compression",
    "core.rag.pipeline",
    "core.rag.chunking",
    "core.rag.hybrid",
    "core.llm.response_generator",
    "core.validation.confidence_scorer",
    "core.validation.quality_metrics",
    "core.websocket_manager",
    "api.auth",
    "api.deps",
    "api.middleware",
]

# Modules that may need optional deps (test import but allow ImportError)
OPTIONAL_MODULES = [
    "core.llm_interface.intelligent_router",
    "core.llm_interface.unified_llm_client",
    "core.groupagents.mega_agent",
    "core.groupagents.case_agent",
    "core.groupagents.writer_agent",
    "core.groupagents.validator_agent",
    "core.orchestration.pipeline_manager",
    "core.orchestration.parallel_executor",
    "core.services.case_service",
    "core.services.ocr_service",
    "core.services.pdf_package_generator",
    "core.workflows.eb1a.validators.eb1a_validator",
    "core.mcp.config",
    "core.mcp.tool_search",
]


@pytest.mark.parametrize("module_path", CRITICAL_MODULES)
def test_critical_module_imports(module_path: str) -> None:
    """Critical modules must import without any errors."""
    # Remove from cache to get a clean import
    sys.modules.pop(module_path, None)
    mod = importlib.import_module(module_path)
    assert mod is not None, f"Failed to import {module_path}"


@pytest.mark.parametrize("module_path", OPTIONAL_MODULES)
def test_optional_module_imports(module_path: str) -> None:
    """Optional modules should import or raise ImportError (not other errors)."""
    sys.modules.pop(module_path, None)
    try:
        mod = importlib.import_module(module_path)
        assert mod is not None
    except ImportError:
        pytest.skip(f"{module_path} has missing optional dependency")


def test_no_circular_imports_in_core() -> None:
    """Importing core package should not cause circular import errors."""
    for mod_name in list(sys.modules):
        if mod_name.startswith("core."):
            sys.modules.pop(mod_name, None)

    import core  # noqa: F401

    assert "core" in sys.modules


def test_retry_module_deprecation_warning() -> None:
    """Importing resilience names from core.retry should emit DeprecationWarning."""
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from core.retry import CircuitBreaker  # noqa: F401

        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1, "Expected DeprecationWarning for legacy re-export"
        assert "core.resilience" in str(deprecation_warnings[0].message)
