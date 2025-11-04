from __future__ import annotations

import pytest

from core.memory.memory_hierarchy import MemoryHierarchy
from core.memory.models import AuditEvent


@pytest.mark.asyncio
async def test_record_and_retrieve_context():
    hierarchy = MemoryHierarchy()

    event = AuditEvent(
        event_id="evt-1",
        user_id="user-1",
        thread_id="thread-1",
        source="unit-test",
        action="created",
        payload={"summary": "Initial message"},
        tags=["init"],
    )
    await hierarchy.record_event(event, reflect=True)

    context = await hierarchy.load_context(
        thread_id="thread-1",
        query="Initial message",
        user_id="user-1",
    )

    assert context.episodic_events, "episodic events should be present"
    assert any(rec.text for rec in context.reflected), "reflection should yield memory records"
    assert context.rmt_slots == {}, "working memory default is empty dict"


@pytest.mark.asyncio
async def test_timeline_and_snapshot():
    hierarchy = MemoryHierarchy()

    for i in range(3):
        await hierarchy.record_event(
            AuditEvent(
                event_id=f"evt-{i}",
                user_id="user-2",
                thread_id="thread-2",
                source="unit-test",
                action="step",
                payload={"summary": f"step {i}"},
                tags=["flow"],
            ),
            reflect=False,
        )

    timeline = await hierarchy.recent_timeline("thread-2", hours=24)
    assert len(timeline) == 3

    snapshot = await hierarchy.get_thread_snapshot("thread-2")
    assert "step 2" in snapshot
