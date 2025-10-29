"""Integration tests for MemoryManager with production backends."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.memory.memory_manager_v2 import (
    create_dev_memory_manager,
    create_production_memory_manager,
)
from core.memory.models import AuditEvent, MemoryRecord


@pytest.fixture
async def production_memory():
    """Fixture for production memory manager with test namespace."""
    try:
        memory = create_production_memory_manager(namespace="test")
    except Exception as exc:  # pragma: no cover - environment-specific
        pytest.skip(f"Production memory backend unavailable: {exc}")
    return memory
    # Cleanup: delete test data after tests
    # (In production you'd want more sophisticated cleanup)


@pytest.fixture
async def dev_memory():
    """Fixture for dev memory manager."""
    return create_dev_memory_manager()


@pytest.mark.asyncio
async def test_health_check_production(production_memory):
    """Test that production memory manager can connect to all backends."""
    health = await production_memory.health_check()

    assert "semantic" in health
    assert "episodic" in health
    assert "working" in health

    # All should be healthy
    assert all(
        health.values()
    ), f"Some backends are unhealthy: {[k for k, v in health.items() if not v]}"


@pytest.mark.asyncio
async def test_semantic_memory_write_retrieve(production_memory):
    """Test writing and retrieving semantic memories."""
    user_id = f"test_user_{uuid4().hex[:8]}"

    # Create test record
    record = MemoryRecord(
        user_id=user_id,
        text="Test legal knowledge about contract law and obligations",
        type="semantic",
        source="test",
        tags=["test", "contract"],
    )

    # Write
    stored = await production_memory.awrite([record])
    assert len(stored) == 1
    assert stored[0].text == record.text

    # Small delay for Pinecone indexing
    import asyncio

    await asyncio.sleep(1)

    # Retrieve
    results = await production_memory.aretrieve(
        query="contract law obligations", user_id=user_id, topk=5
    )

    assert len(results) > 0, "No results found"
    assert results[0].user_id == user_id
    # Should have non-zero confidence score
    assert results[0].confidence is not None
    assert results[0].confidence > 0.0


@pytest.mark.asyncio
async def test_episodic_memory_audit_trail(production_memory):
    """Test audit event logging and retrieval."""
    thread_id = f"test_thread_{uuid4().hex[:8]}"
    user_id = "test_user"

    # Create and log events
    events = [
        AuditEvent(
            event_id=str(uuid4()),
            user_id=user_id,
            thread_id=thread_id,
            source="test",
            action="test_action_1",
            payload={"data": "test1"},
        ),
        AuditEvent(
            event_id=str(uuid4()),
            user_id=user_id,
            thread_id=thread_id,
            source="test",
            action="test_action_2",
            payload={"data": "test2"},
        ),
    ]

    for event in events:
        await production_memory.alog_audit(event)

    # Retrieve thread snapshot
    snapshot = await production_memory.asnapshot_thread(thread_id)

    assert len(snapshot) > 0
    assert "test_action_1" in snapshot
    assert "test_action_2" in snapshot


@pytest.mark.asyncio
async def test_rmt_buffer_set_get(production_memory):
    """Test RMT buffer operations."""
    thread_id = f"test_thread_{uuid4().hex[:8]}"

    # Set RMT slots
    slots = {
        "persona": "test persona",
        "long_term_facts": "test facts",
        "open_loops": "test loops",
        "recent_summary": "test summary",
    }

    await production_memory.aset_rmt(thread_id, slots)

    # Get RMT slots
    retrieved = await production_memory.aget_rmt(thread_id)

    assert retrieved is not None
    assert retrieved["persona"] == "test persona"
    assert retrieved["long_term_facts"] == "test facts"


@pytest.mark.asyncio
async def test_reflect_from_audit_event(production_memory):
    """Test reflection: converting AuditEvent to MemoryRecord."""
    user_id = f"test_user_{uuid4().hex[:8]}"

    # Create audit event
    event = AuditEvent(
        event_id=str(uuid4()),
        user_id=user_id,
        thread_id="test_thread",
        source="test",
        action="important_decision",
        payload={
            "decision": "Approved I-485 application",
            "reason": "All documentation complete",
        },
    )

    # Write (should trigger reflection)
    records = await production_memory.awrite(event)

    # Should create at least one memory record
    assert len(records) > 0
    assert records[0].user_id == user_id


@pytest.mark.asyncio
async def test_dev_memory_in_memory():
    """Test that dev memory uses in-memory stores."""
    memory = create_dev_memory_manager()

    # Check that stores are in-memory (OrderedDict with LRU/TTL)
    assert hasattr(memory.semantic, "_items"), "Should be in-memory store"
    from collections import OrderedDict

    assert isinstance(memory.semantic._items, OrderedDict), "Should use OrderedDict for LRU"

    # Test basic operations
    record = MemoryRecord(user_id="test", text="test memory", type="semantic", source="test")

    await memory.awrite([record])
    results = await memory.aretrieve("test memory", user_id="test")

    assert len(results) > 0


@pytest.mark.asyncio
async def test_consolidate(production_memory):
    """Test memory consolidation."""
    stats = await production_memory.aconsolidate(user_id="test_user")

    assert isinstance(stats.total_after, int)
    assert stats.total_after >= 0


@pytest.mark.asyncio
async def test_multiple_users_isolation(production_memory):
    """Test that memories are properly isolated by user_id."""
    user1 = f"user1_{uuid4().hex[:8]}"
    user2 = f"user2_{uuid4().hex[:8]}"

    # Create records for different users
    record1 = MemoryRecord(
        user_id=user1, text="User 1 private information", type="semantic", source="test"
    )
    record2 = MemoryRecord(
        user_id=user2, text="User 2 private information", type="semantic", source="test"
    )

    await production_memory.awrite([record1, record2])

    import asyncio

    await asyncio.sleep(1)  # Wait for indexing

    # Retrieve for user1 - should not see user2's data
    results_user1 = await production_memory.aretrieve("private information", user_id=user1, topk=10)

    assert len(results_user1) > 0
    assert all(r.user_id == user1 for r in results_user1), "Found other user's data!"


if __name__ == "__main__":
    # Run with: pytest tests/integration/memory/test_memory_integration.py -v
    pytest.main([__file__, "-v", "-s"])
