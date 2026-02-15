"""Tests for DI container (core/di/container.py)."""

from __future__ import annotations

import pytest

from core.di.container import Container, get_container, reset_container


class TestContainer:
    """Test the DI Container class."""

    def setup_method(self):
        self.container = Container()

    def test_register_and_get_singleton(self):
        obj = {"key": "value"}
        self.container.register_singleton("config", obj)
        assert self.container.get("config") is obj

    def test_get_missing_key_raises(self):
        with pytest.raises(KeyError, match="Dependency not found: missing"):
            self.container.get("missing")

    def test_has_registered(self):
        self.container.register_singleton("x", 42)
        assert self.container.has("x") is True
        assert self.container.has("y") is False

    def test_has_factory(self):
        self.container.register_factory("f", lambda: "created")
        assert self.container.has("f") is True

    def test_has_async_factory(self):
        async def factory():
            return "async_val"

        self.container.register_factory("af", factory, is_async=True)
        assert self.container.has("af") is True

    def test_register_factory_creates_on_get(self):
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        self.container.register_factory("svc", factory)
        r1 = self.container.get("svc")
        r2 = self.container.get("svc")
        # Factory is called each time (not cached)
        assert r1["count"] == 1
        assert r2["count"] == 2

    def test_get_or_create_singleton_lazy(self):
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        r1 = self.container.get_or_create_singleton("lazy", factory)
        r2 = self.container.get_or_create_singleton("lazy", factory)
        assert r1 == "instance_1"
        assert r2 == "instance_1"  # Same instance returned
        assert call_count == 1  # Factory called only once

    def test_singleton_overwrite(self):
        self.container.register_singleton("key", "first")
        self.container.register_singleton("key", "second")
        assert self.container.get("key") == "second"

    def test_clear(self):
        self.container.register_singleton("a", 1)
        self.container.register_factory("b", lambda: 2)
        self.container.clear()
        assert self.container.has("a") is False
        assert self.container.has("b") is False

    def test_list_dependencies(self):
        self.container.register_singleton("s", "val")
        self.container.register_factory("f", lambda: "val")
        self.container.register_factory("af", lambda: "val", is_async=True)
        deps = self.container.list_dependencies()
        assert deps["s"] == "singleton"
        assert deps["f"] == "factory"
        assert deps["af"] == "async_factory"

    @pytest.mark.asyncio
    async def test_aget_singleton(self):
        self.container.register_singleton("s", "sync_val")
        result = await self.container.aget("s")
        assert result == "sync_val"

    @pytest.mark.asyncio
    async def test_aget_async_factory(self):
        async def factory():
            return "async_created"

        self.container.register_factory("af", factory, is_async=True)
        result = await self.container.aget("af")
        assert result == "async_created"

    @pytest.mark.asyncio
    async def test_aget_sync_factory_fallback(self):
        self.container.register_factory("sf", lambda: "sync_created")
        result = await self.container.aget("sf")
        assert result == "sync_created"

    @pytest.mark.asyncio
    async def test_aget_missing_raises(self):
        with pytest.raises(KeyError):
            await self.container.aget("missing")


class TestGlobalContainer:
    """Test module-level container functions."""

    def setup_method(self):
        reset_container()

    def test_get_container_returns_same_instance(self):
        c1 = get_container()
        c2 = get_container()
        assert c1 is c2

    def test_reset_container_creates_new(self):
        c1 = get_container()
        reset_container()
        c2 = get_container()
        assert c1 is not c2
