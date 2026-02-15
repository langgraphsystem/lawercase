"""
Verify Supabase RFE data and configure RAGPipelineAgent.

This script:
1. Connects to Supabase
2. Queries for RFE-related records
3. Displays available data
4. Tests RAGPipelineAgent connection
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from core.di.container import get_container
from core.groupagents.rag_pipeline_agent import RagPipelineAgent

# Load environment variables
load_dotenv()


async def main():
    print("🔍 Verifying Supabase RFE Data Connection\n")
    print("=" * 60)

    # Step 1: Initialize container and get memory manager
    print("\n1️⃣ Initializing Memory Manager...")
    container = get_container()
    memory_manager = container.get("memory_manager")

    if not memory_manager:
        print("❌ Memory Manager not found in container!")
        return

    print("✅ Memory Manager initialized")

    # Step 2: Initialize RAGPipelineAgent
    print("\n2️⃣ Initializing RAGPipelineAgent...")
    rag_agent = RagPipelineAgent(memory_manager=memory_manager)
    print("✅ RAGPipelineAgent initialized")
    print(f"   Cache TTL: {rag_agent.cache_ttl}s")

    # Step 3: Check Supabase semantic store
    print("\n3️⃣ Checking Supabase Semantic Store...")
    semantic_store = memory_manager.semantic

    if not semantic_store:
        print("❌ Semantic store not available!")
        return

    # Health check
    is_healthy = await semantic_store.health_check()
    print(f"   Health: {'✅ OK' if is_healthy else '❌ FAILED'}")

    # Count total records
    total_count = await semantic_store.acount()
    print(f"   Total records in DB: {total_count}")

    # Step 4: Search for RFE-related records
    print("\n4️⃣ Searching for RFE-related data...")

    # Try different search terms
    search_terms = [
        "RFE",
        "Request for Evidence",
        "rejection",
        "denial",
        "Kazarian",
        "precedent",
        "case law",
    ]

    results_found = False

    for term in search_terms:
        print(f"\n   🔎 Searching for: '{term}'")
        records = await semantic_store.aretrieve(query=term, topk=5)

        if records:
            results_found = True
            print(f"   ✅ Found {len(records)} relevant records:")
            for i, record in enumerate(records, 1):
                print(f"\n   [{i}] ID: {record.id[:12]}...")
                print(f"       Tags: {', '.join(record.tags or [])}")
                print(f"       Source: {record.source}")
                print(f"       Confidence: {record.confidence:.2%}")
                print(f"       Text preview: {record.text[:150]}...")
        else:
            print("   ❌ No records found")

    if not results_found:
        print("\n⚠️  WARNING: No RFE-related data found in database!")
        print("   You may need to load Kazarian and other precedents first.")

    # Step 5: Test RAG query
    print("\n5️⃣ Testing RAG Query...")
    test_query = "What are common reasons for EB-1A RFE or denial?"

    print(f"   Query: '{test_query}'")
    answer = await rag_agent.arag(test_query, topk=5)

    print(f"\n   Answer confidence: {answer.confidence:.2%}")
    print(f"   Sources found: {len(answer.sources)}")
    print(f"   Retrieval time: {answer.retrieval_time_ms:.0f}ms")
    print("\n   Generated answer:")
    print(f"   {answer.answer[:300]}...")

    if answer.sources:
        print("\n   📚 Top sources:")
        for i, source in enumerate(answer.sources[:3], 1):
            print(f"   [{i}] {source.source_type} | Relevance: {source.relevance_score:.2%}")
            print(f"       {source.content[:100]}...")

    # Step 6: Display statistics
    print("\n6️⃣ RAG Agent Statistics:")
    stats = rag_agent.get_stats()
    print(f"   Total queries: {stats['total_queries']}")
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Cache misses: {stats['cache_misses']}")
    print(f"   Cache hit rate: {stats['cache_hit_rate']:.2%}")
    print(f"   Cache size: {stats['cache_size']}")
    print(f"   Avg retrieval time: {stats['avg_retrieval_time_ms']:.0f}ms")

    # Step 7: Recommendations
    print("\n" + "=" * 60)
    print("📋 RECOMMENDATIONS:")
    print("=" * 60)

    if not results_found:
        print("\n🔴 CRITICAL: No RFE/precedent data found!")
        print("   Next steps:")
        print("   1. Load Kazarian case data")
        print("   2. Import real RFE cases from your database")
        print("   3. Add USCIS policy manual excerpts")
        print("\n   I can help you create a data loading script.")
    else:
        print("\n🟢 GOOD: RFE data is present in database!")
        print("   Optimization suggestions:")
        print("   1. Consider upgrading to hybrid search (keyword + embedding)")
        print("   2. Add LLM-based answer generation (currently using templates)")
        print("   3. Implement reranking for better result quality")

    print("\n✨ Verification complete!")


if __name__ == "__main__":
    asyncio.run(main())
