"""Tests for DI container."""

import pytest

from core.di import Container, get_container, reset_container


class TestContainer:
    """Test container functionality."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Reset container after each test."""
        reset_container()

    def test_container_singleton_registration(self):
        """Container should register and retrieve singletons."""
        container = Container()

        # Register singleton
        test_obj = {"value": 42}
        container.register_singleton("test", test_obj)

        # Retrieve singleton
        retrieved = container.get("test")
        assert retrieved is test_obj
        assert retrieved["value"] == 42

    def test_container_factory_registration(self):
        """Container should create instances from factories."""
        container = Container()

        # Register factory
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        container.register_factory("test", factory)

        # Each get() should call factory
        obj1 = container.get("test")
        obj2 = container.get("test")

        assert obj1["count"] == 1
        assert obj2["count"] == 2
        assert call_count == 2

    def test_container_has(self):
        """Container should check if dependency exists."""
        container = Container()

        assert not container.has("test")

        container.register_singleton("test", {})
        assert container.has("test")

    def test_container_get_not_found(self):
        """Container should raise KeyError for missing dependencies."""
        container = Container()

        with pytest.raises(KeyError, match="Dependency not found: missing"):
            container.get("missing")

    def test_container_get_or_create_singleton(self):
        """Container should create singleton on first access."""
        container = Container()

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        # First call creates singleton
        obj1 = container.get_or_create_singleton("test", factory)
        assert obj1["count"] == 1
        assert call_count == 1

        # Second call returns same instance
        obj2 = container.get_or_create_singleton("test", factory)
        assert obj2 is obj1
        assert call_count == 1  # Factory not called again

    def test_container_clear(self):
        """Container should clear all dependencies."""
        container = Container()

        container.register_singleton("test1", {})
        container.register_factory("test2", lambda: {})

        assert container.has("test1")
        assert container.has("test2")

        container.clear()

        assert not container.has("test1")
        assert not container.has("test2")

    def test_container_list_dependencies(self):
        """Container should list all registered dependencies."""
        container = Container()

        container.register_singleton("singleton1", {})
        container.register_factory("factory1", lambda: {})

        deps = container.list_dependencies()

        assert "singleton1" in deps
        assert "factory1" in deps
        assert deps["singleton1"] == "singleton"
        assert deps["factory1"] == "factory"

    @pytest.mark.asyncio
    async def test_container_async_factory(self):
        """Container should support async factories."""
        container = Container()

        async def async_factory():
            return {"async": True}

        container.register_factory("async_test", async_factory, is_async=True)

        result = await container.aget("async_test")
        assert result["async"] is True

    @pytest.mark.asyncio
    async def test_container_aget_fallback_to_sync(self):
        """Container should fallback to sync factory if no async factory."""
        container = Container()

        def sync_factory():
            return {"sync": True}

        container.register_factory("test", sync_factory)

        # aget should work with sync factory
        result = await container.aget("test")
        assert result["sync"] is True


class TestGlobalContainer:
    """Test global container functions."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Reset container after each test."""
        reset_container()

    def test_get_container_singleton(self):
        """get_container() should return same instance."""
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_get_container_initialized(self):
        """get_container() should initialize with default dependencies."""
        container = get_container()

        # Should have default dependencies
        assert container.has("memory_manager")
        assert container.has("tool_registry")
        assert container.has("mega_agent")

    def test_get_container_mega_agent(self):
        """get_container() should provide MegaAgent."""
        container = get_container()

        mega_agent = container.get("mega_agent")
        assert mega_agent is not None
        assert hasattr(mega_agent, "handle_command")

    def test_reset_container(self):
        """reset_container() should clear global container."""
        container1 = get_container()
        reset_container()
        container2 = get_container()

        # Should be different instances
        assert container1 is not container2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
