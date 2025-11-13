"""Dependency Injection container for MegaAgent Pro.

Provides centralized dependency management to ensure:
- Single shared instances between API and Telegram bot
- Easy testing with mock dependencies
- Clear dependency graph
- Lifecycle management
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class Container:
    """Dependency Injection container.

    Manages singleton instances and factory functions for creating dependencies.
    Supports both sync and async dependency resolution.

    Example:
        >>> container = Container()
        >>> container.register_singleton("config", Settings())
        >>> config = container.get("config")
    """

    def __init__(self) -> None:
        """Initialize empty container."""
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._async_factories: dict[str, Callable[[], Awaitable[Any]]] = {}
        logger.info("di.container.initialized")

    def register_singleton(self, key: str, instance: Any) -> None:
        """Register singleton instance.

        Args:
            key: Unique identifier for the dependency
            instance: The singleton instance to register

        Example:
            >>> container.register_singleton("memory", MemoryManager())
        """
        if key in self._singletons:
            logger.warning("di.container.singleton_overwrite", key=key)
        self._singletons[key] = instance
        logger.debug("di.container.singleton_registered", key=key, type=type(instance).__name__)

    def register_factory(
        self, key: str, factory: Callable[[], T], *, is_async: bool = False
    ) -> None:
        """Register factory function for creating dependencies.

        Args:
            key: Unique identifier for the dependency
            factory: Function that creates the dependency
            is_async: Whether the factory is async

        Example:
            >>> def create_agent():
            ...     return MegaAgent(memory=container.get("memory"))
            >>> container.register_factory("agent", create_agent)
        """
        if is_async:
            self._async_factories[key] = factory  # type: ignore
            logger.debug("di.container.async_factory_registered", key=key)
        else:
            self._factories[key] = factory  # type: ignore
            logger.debug("di.container.factory_registered", key=key)

    def get(self, key: str) -> Any:
        """Get dependency synchronously.

        Args:
            key: Unique identifier for the dependency

        Returns:
            The dependency instance

        Raises:
            KeyError: If dependency not found

        Example:
            >>> memory = container.get("memory_manager")
        """
        # Check singletons first
        if key in self._singletons:
            logger.debug("di.container.get_singleton", key=key)
            return self._singletons[key]

        # Check factories
        if key in self._factories:
            logger.debug("di.container.create_from_factory", key=key)
            instance = self._factories[key]()
            return instance

        logger.error("di.container.dependency_not_found", key=key)
        raise KeyError(f"Dependency not found: {key}")

    async def aget(self, key: str) -> Any:
        """Get dependency asynchronously.

        Args:
            key: Unique identifier for the dependency

        Returns:
            The dependency instance

        Raises:
            KeyError: If dependency not found

        Example:
            >>> memory = await container.aget("memory_manager")
        """
        # Check singletons
        if key in self._singletons:
            logger.debug("di.container.aget_singleton", key=key)
            return self._singletons[key]

        # Check async factories
        if key in self._async_factories:
            logger.debug("di.container.create_from_async_factory", key=key)
            instance = await self._async_factories[key]()
            return instance

        # Fallback to sync factories
        if key in self._factories:
            logger.debug("di.container.aget_from_sync_factory", key=key)
            return self._factories[key]()

        logger.error("di.container.dependency_not_found", key=key)
        raise KeyError(f"Dependency not found: {key}")

    def get_or_create_singleton(self, key: str, factory: Callable[[], T]) -> T:
        """Get existing singleton or create new one.

        Args:
            key: Unique identifier for the dependency
            factory: Function to create the dependency if it doesn't exist

        Returns:
            The dependency instance

        Example:
            >>> memory = container.get_or_create_singleton(
            ...     "memory", lambda: MemoryManager()
            ... )
        """
        if key not in self._singletons:
            logger.info("di.container.lazy_singleton_create", key=key)
            self._singletons[key] = factory()
        return self._singletons[key]

    def has(self, key: str) -> bool:
        """Check if dependency is registered.

        Args:
            key: Unique identifier for the dependency

        Returns:
            True if dependency exists

        Example:
            >>> if container.has("memory_manager"):
            ...     memory = container.get("memory_manager")
        """
        return key in self._singletons or key in self._factories or key in self._async_factories

    def clear(self) -> None:
        """Clear all registered dependencies.

        Useful for testing.

        Example:
            >>> container.clear()  # Reset for next test
        """
        logger.warning("di.container.clear_all")
        self._singletons.clear()
        self._factories.clear()
        self._async_factories.clear()

    def list_dependencies(self) -> dict[str, str]:
        """Get list of all registered dependencies.

        Returns:
            Dict mapping dependency key to type (singleton/factory/async_factory)

        Example:
            >>> deps = container.list_dependencies()
            >>> print(deps)
            {'memory_manager': 'singleton', 'mega_agent': 'factory'}
        """
        deps = {}
        for key in self._singletons:
            deps[key] = "singleton"
        for key in self._factories:
            deps[key] = "factory"
        for key in self._async_factories:
            deps[key] = "async_factory"
        return deps


# Global container instance
_container: Container | None = None


def get_container() -> Container:
    """Get global DI container.

    Lazily initializes the container on first access.

    Returns:
        The global container instance

    Example:
        >>> container = get_container()
        >>> memory = container.get("memory_manager")
    """
    global _container
    if _container is None:
        logger.info("di.container.global_init")
        _container = Container()
        _initialize_container(_container)
    return _container


def reset_container() -> None:
    """Reset global container.

    Useful for testing to ensure clean state.

    Example:
        >>> reset_container()  # Reset for next test
    """
    global _container
    logger.warning("di.container.global_reset")
    _container = None


def _initialize_container(container: Container) -> None:
    """Initialize container with default dependencies.

    Args:
        container: The container to initialize

    Registers:
        - memory_manager: MemoryManager singleton
        - tool_registry: ToolRegistry singleton
        - mega_agent: MegaAgent factory (creates new instance on each get)
    """
    from core.groupagents.mega_agent import MegaAgent
    from core.memory.memory_manager import MemoryManager
    from core.tools.tool_registry import get_tool_registry

    logger.info("di.container.initializing_defaults")

    # Singletons - shared across all components
    container.register_singleton("memory_manager", MemoryManager())
    container.register_singleton("tool_registry", get_tool_registry())

    # Factories - create on demand
    def create_mega_agent() -> MegaAgent:
        """Create MegaAgent with injected dependencies."""
        memory = container.get("memory_manager")
        logger.debug("di.container.creating_mega_agent")
        return MegaAgent(
            memory_manager=memory,
            use_chain_of_thought=True,  # Enable CoT by default
        )

    container.register_factory("mega_agent", create_mega_agent)

    logger.info(
        "di.container.initialized_defaults",
        dependencies=list(container.list_dependencies().keys()),
    )
