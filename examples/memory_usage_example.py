"""
Complete example of using the new MemoryManager with Pinecone + PostgreSQL.

This example demonstrates:
- Setting up production memory manager
- Storing semantic memories
- Vector similarity search
- Audit trail logging
- RMT buffer management
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

# Set environment to use production stores
os.environ["ENV"] = "production"

from core.memory.memory_manager_v2 import create_production_memory_manager
from core.memory.models import AuditEvent, MemoryRecord


async def example_semantic_memory():
    """Example: Store and retrieve semantic memories."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Semantic Memory (Pinecone + Voyage AI)")
    print("=" * 60)

    # Initialize production memory manager
    memory = create_production_memory_manager(namespace="examples")

    # Check health
    health = await memory.health_check()
    print(f"\n✅ Health Check: {health}")

    # Create some legal knowledge records
    records = [
        MemoryRecord(
            user_id="lawyer_001",
            text="The Smith v. Jones precedent establishes that contract obligations "
            "persist even after verbal amendments if not documented in writing.",
            type="semantic",
            source="case_law",
            tags=["contract", "precedent", "smith-v-jones"],
        ),
        MemoryRecord(
            user_id="lawyer_001",
            text="In immigration law, Form I-485 is used to register permanent residence "
            "or adjust status. It must be filed while the applicant is in the US.",
            type="semantic",
            source="immigration_guide",
            tags=["immigration", "i-485", "adjustment-of-status"],
        ),
        MemoryRecord(
            user_id="lawyer_001",
            text="The statute of limitations for filing a personal injury claim in California "
            "is two years from the date of injury.",
            type="semantic",
            source="statute",
            tags=["personal-injury", "california", "statute-of-limitations"],
        ),
    ]

    # Store records (embeddings generated automatically)
    print(f"\n📝 Storing {len(records)} knowledge records...")
    stored = await memory.awrite(records)
    print(f"✅ Stored {len(stored)} records with {len(stored[0].embedding or [])}D embeddings")

    # Search using semantic similarity
    print("\n🔍 Searching for 'immigration form requirements'...")
    results = await memory.aretrieve(
        query="immigration form requirements", user_id="lawyer_001", topk=3
    )

    print(f"\n📊 Found {len(results)} relevant results:")
    for i, result in enumerate(results, 1):
        confidence = result.confidence or 0.0
        print(f"\n  {i}. Score: {confidence:.3f}")
        print(f"     Text: {result.text[:100]}...")
        print(f"     Tags: {result.tags}")

    return memory


async def example_audit_trail():
    """Example: Log and retrieve audit events."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Audit Trail (PostgreSQL Episodic Memory)")
    print("=" * 60)

    memory = create_production_memory_manager(namespace="examples")

    thread_id = "case_12345"

    # Log series of events for a case
    events = [
        AuditEvent(
            event_id=str(uuid4()),
            user_id="lawyer_001",
            thread_id=thread_id,
            source="case_agent",
            action="create_case",
            payload={"case_id": "case_12345", "title": "Smith Immigration Case"},
            tags=["case", "create"],
        ),
        AuditEvent(
            event_id=str(uuid4()),
            user_id="lawyer_001",
            thread_id=thread_id,
            source="document_agent",
            action="upload_document",
            payload={"document_id": "doc_001", "type": "i-485"},
            tags=["document", "upload"],
        ),
        AuditEvent(
            event_id=str(uuid4()),
            user_id="lawyer_001",
            thread_id=thread_id,
            source="validator_agent",
            action="validate_document",
            payload={"document_id": "doc_001", "status": "valid"},
            tags=["validation", "success"],
        ),
    ]

    print(f"\n📝 Logging {len(events)} audit events...")
    for event in events:
        await memory.alog_audit(event)
    print(f"✅ Logged {len(events)} events for thread {thread_id}")

    # Retrieve thread history
    print(f"\n📜 Retrieving audit trail for thread {thread_id}...")
    snapshot = await memory.asnapshot_thread(thread_id)

    print("\n📊 Thread Snapshot:")
    print("-" * 60)
    print(snapshot)
    print("-" * 60)

    return memory


async def example_rmt_buffer():
    """Example: Working memory (RMT buffers)."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: RMT Buffer (PostgreSQL Working Memory)")
    print("=" * 60)

    memory = create_production_memory_manager(namespace="examples")

    thread_id = "conversation_456"

    # Set RMT slots
    rmt_slots = {
        "persona": "Experienced immigration lawyer specializing in family-based cases",
        "long_term_facts": "Client prefers email communication. Previous case was I-130 petition.",
        "open_loops": "Waiting for client's birth certificate. Follow up on Friday.",
        "recent_summary": "Discussed I-485 requirements. Client understands the process.",
    }

    print(f"\n📝 Setting RMT buffer for thread {thread_id}...")
    await memory.aset_rmt(thread_id, rmt_slots)
    print("✅ RMT buffer stored")

    # Retrieve RMT slots
    print("\n📖 Retrieving RMT buffer...")
    retrieved_slots = await memory.aget_rmt(thread_id)

    if retrieved_slots:
        print("\n📊 RMT Slots:")
        print("-" * 60)
        for key, value in retrieved_slots.items():
            print(f"  {key:20s}: {value}")
        print("-" * 60)

    return memory


async def example_full_workflow():
    """Example: Complete workflow with all memory types."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Full Workflow (All Memory Types)")
    print("=" * 60)

    memory = create_production_memory_manager(namespace="examples")

    user_id = "lawyer_001"
    case_id = "case_67890"
    thread_id = f"case_{case_id}"

    # 1. Log case creation
    print("\n📝 Step 1: Log case creation...")
    await memory.alog_audit(
        AuditEvent(
            event_id=str(uuid4()),
            user_id=user_id,
            thread_id=thread_id,
            source="workflow",
            action="case_created",
            payload={"case_id": case_id, "type": "immigration"},
        )
    )

    # 2. Store case knowledge
    print("📝 Step 2: Store case-specific knowledge...")
    case_knowledge = [
        MemoryRecord(
            user_id=user_id,
            text=f"Case {case_id}: Client is applying for adjustment of status based on marriage to US citizen.",
            type="semantic",
            source="case_notes",
            tags=["case", case_id, "aos"],
        )
    ]
    await memory.awrite(case_knowledge)

    # 3. Set RMT context
    print("📝 Step 3: Set working memory context...")
    await memory.aset_rmt(
        thread_id,
        {
            "persona": "Immigration attorney",
            "long_term_facts": f"Working on case {case_id}",
            "open_loops": "Pending I-693 medical exam",
            "recent_summary": "Prepared I-485 package",
        },
    )

    # 4. Search for relevant precedents
    print("\n🔍 Step 4: Search for relevant legal knowledge...")
    results = await memory.aretrieve(
        query="adjustment of status marriage requirements", user_id=user_id, topk=3
    )

    print("\n✅ Workflow Complete!")
    print("   - Audit events: Logged")
    print(f"   - Semantic memory: {len(results)} relevant records found")
    print("   - RMT buffer: Active")

    return memory


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("🚀 MemoryManager Production Examples")
    print("=" * 60)

    try:
        # Run examples
        await example_semantic_memory()
        await example_audit_trail()
        await example_rmt_buffer()
        await example_full_workflow()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Note: Make sure .env is configured with:
    # - POSTGRES_DSN
    # - PINECONE_API_KEY
    # - VOYAGE_API_KEY
    # - R2 credentials

    asyncio.run(main())
