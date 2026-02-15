"""
Direct Supabase RFE data verification (bypassing DI container).
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def main():
    print("🔍 Checking Supabase RFE Data (Direct Connection)\n")
    print("=" * 60)

    # Step 1: Initialize Supabase store directly
    print("\n1️⃣ Connecting to Supabase...")

    try:
        from core.memory.stores.supabase_semantic_store import SupabaseSemanticStore

        store = SupabaseSemanticStore(namespace="default")
        print("✅ Connected to Supabase")

        # Health check
        is_healthy = await store.health_check()
        print(f"   Health: {'✅ OK' if is_healthy else '❌ FAILED'}")

        if not is_healthy:
            print("\n❌ Supabase connection failed!")
            print("   Check your .env file for:")
            print("   - SUPABASE_URL")
            print("   - SUPABASE_KEY")
            return

        # Count total records
        total_count = await store.acount()
        print(f"   Total records: {total_count}")

    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return

    # Step 2: Search for RFE data
    print("\n2️⃣ Searching for RFE-related data...")

    search_terms = {
        "RFE": "Request for Evidence",
        "Kazarian": "Leading EB-1A precedent case",
        "denial": "Denial reasons and patterns",
        "rejection": "Rejection analysis",
        "USCIS": "USCIS policy and guidelines",
        "precedent": "Legal precedents",
        "criteria": "EB-1A criteria analysis",
    }

    all_results = {}

    for term, description in search_terms.items():
        print(f"\n   🔎 '{term}' ({description})")

        try:
            records = await store.aretrieve(query=term, topk=3)

            all_results[term] = records

            if records:
                print(f"   ✅ Found {len(records)} records")
                for i, record in enumerate(records[:2], 1):
                    tags_str = ", ".join(record.tags or ["no tags"])
                    print(f"      [{i}] Tags: [{tags_str}]")
                    print(f"          Preview: {record.text[:100]}...")
            else:
                print("   ❌ No results")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Step 3: Analyze findings
    print("\n" + "=" * 60)
    print("📊 ANALYSIS:")
    print("=" * 60)

    total_unique_records = len({r.id for results in all_results.values() for r in results})
    has_data = any(len(results) > 0 for results in all_results.values())

    print(f"\n   Total unique relevant records: {total_unique_records}")

    if has_data:
        print("\n   ✅ RFE/Precedent data IS available in database!")
        print("\n   📋 Data distribution:")
        for term, records in all_results.items():
            if records:
                print(f"      • {term}: {len(records)} records")

        print("\n   🎯 RAGPipelineAgent can use this data for:")
        print("      1. Finding similar RFE cases")
        print("      2. Identifying common denial patterns")
        print("      3. Recommending strategies based on precedents")

        print("\n   💡 Optimization suggestions:")
        print("      1. Add more legal precedents (Kazarian, Buletini, etc.)")
        print("      2. Tag records with specific criteria (awards, press, etc.)")
        print("      3. Include USCIS policy manual sections")

    else:
        print("\n   ⚠️  NO RFE/precedent data found!")
        print("\n   📝 Recommended actions:")
        print("      1. Create Kazarian case loader")
        print("      2. Import your RFE case database")
        print("      3. Add USCIS policy excerpts")
        print("\n      I can help create these loaders.")

    # Step 4: Test a complex query
    if has_data:
        print("\n" + "=" * 60)
        print("🧪 TESTING COMPLEX QUERY:")
        print("=" * 60)

        test_query = "programmer with low citations received RFE for insufficient press coverage"
        print(f"\nQuery: '{test_query}'")

        try:
            results = await store.aretrieve(query=test_query, topk=5)

            if results:
                print(f"\n✅ Found {len(results)} relevant cases!")
                print("\nTop matches:")
                for i, result in enumerate(results[:3], 1):
                    conf = result.confidence if hasattr(result, "confidence") else 0.0
                    print(f"\n[{i}] Confidence: {conf:.1%}")
                    print(f"    Tags: {', '.join(result.tags or [])}")
                    print(f"    {result.text[:200]}...")
            else:
                print("\n❌ No matches for this complex query")
                print("   → May need more training data")
        except Exception as e:
            print(f"\n❌ Query failed: {e}")

    print("\n" + "=" * 60)
    print("✨ Verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
