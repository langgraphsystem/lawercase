"""Knowledge Graph System Example.

This example demonstrates how to:
1. Build a knowledge graph from text documents
2. Query the graph with graph-enhanced RAG
3. Visualize entity subgraphs
4. Use hybrid retrieval strategies
"""

from __future__ import annotations

import asyncio

from core.knowledge_graph import (GraphConstructor, GraphRAGQuery, GraphStore,
                                  HybridRAG)

# Sample legal documents for demo
LEGAL_DOCUMENTS = [
    """
    John Smith works at Acme Corporation. He is a Senior Attorney at Acme Corporation.
    Acme Corporation is located in New York.
    """,
    """
    Jane Doe graduated from Harvard Law School. She founded Smith & Doe LLC.
    Smith & Doe LLC is a subsidiary of Legal Holdings Inc.
    """,
    """
    Robert Johnson owns Johnson Properties Ltd. The company was founded in 2010.
    Robert Johnson born in California.
    """,
    """
    Sarah Williams is a Partner at Baker & Associates Corp. She specializes in corporate law.
    Baker & Associates Corp. located in San Francisco.
    """,
]


def demonstrate_graph_construction():
    """Demonstrate building a knowledge graph."""
    print("=" * 60)
    print("1. KNOWLEDGE GRAPH CONSTRUCTION")
    print("=" * 60)

    # Initialize graph constructor
    constructor = GraphConstructor()

    # Process documents
    for i, doc in enumerate(LEGAL_DOCUMENTS):
        print(f"\n📄 Processing Document {i + 1}...")
        result = constructor.add_document(
            doc,
            doc_id=f"doc_{i}",
            metadata={"source": "legal_documents"},
        )

        print(f"   Entities found: {result['entities_found']}")
        print(f"   Relations found: {result['relations_found']}")
        print(f"   Nodes added: {result['nodes_added']}")
        print(f"   Edges added: {result['edges_added']}")

        # Show extracted entities
        if result["entities"]:
            print("\n   Extracted Entities:")
            for entity in result["entities"][:3]:  # Show first 3
                print(f"     - {entity['text']} ({entity['type']})")

        # Show extracted relations
        if result["relations"]:
            print("\n   Extracted Relations:")
            for rel in result["relations"][:3]:  # Show first 3
                print(
                    f"     - {rel['subject']} --[{rel['relation']}]--> {rel['object']}",
                )

    # Get graph statistics
    print("\n" + "=" * 60)
    print("GRAPH STATISTICS")
    print("=" * 60)
    stats = constructor.get_statistics()
    graph_stats = stats["graph_stats"]
    print(f"Total Nodes: {graph_stats['num_nodes']}")
    print(f"Total Edges: {graph_stats['num_edges']}")
    print(f"Cached Entities: {stats['cached_entities']}")
    print("\nEntity Types:")
    for entity_type, count in stats["entity_types"].items():
        print(f"  {entity_type}: {count}")

    return constructor


def demonstrate_entity_context(constructor: GraphConstructor):
    """Demonstrate entity context retrieval."""
    print("\n" + "=" * 60)
    print("2. ENTITY CONTEXT RETRIEVAL")
    print("=" * 60)

    # Test entities
    test_entities = ["John Smith", "Acme Corporation", "Jane Doe"]

    for entity in test_entities:
        print(f"\n🔍 Context for '{entity}':")
        context = constructor.get_entity_context(entity, max_hops=2)

        if context["found"]:
            print(f"   Entity ID: {context['entity_id']}")
            print(
                f"   Direct neighbors: {context['node_info'].get('neighbors_count', 0) if context.get('node_info') else 0}",
            )

            # Show direct relationships
            neighbors = context.get("direct_neighbors", [])
            if neighbors:
                print(f"   Connected to: {', '.join(neighbors[:5])}")

            # Show related entities
            related = context.get("related_entities", {})
            if related:
                print(f"   Related entities (within 2 hops): {len(related)}")
        else:
            print("   ❌ Entity not found in graph")


async def demonstrate_graph_rag(constructor: GraphConstructor):
    """Demonstrate graph-enhanced RAG queries."""
    print("\n" + "=" * 60)
    print("3. GRAPH-ENHANCED RAG QUERIES")
    print("=" * 60)

    # Initialize graph RAG
    graph_rag = GraphRAGQuery(constructor.get_graph())

    # Test queries
    queries = [
        "Tell me about John Smith",
        "Who works at Acme Corporation?",
        "What do you know about Jane Doe?",
    ]

    for query in queries:
        print(f"\n💬 Query: '{query}'")

        result = await graph_rag.query(
            query,
            top_k=5,
            expand_hops=2,
            rerank=True,
        )

        print(f"   Query entities detected: {result.metadata['query_entities']}")
        print(
            f"   Graph-expanded results: {len(result.graph_expanded)}",
        )

        # Show top results
        if result.reranked_results:
            print("\n   Top Results:")
            for i, res in enumerate(result.reranked_results[:3], 1):
                entity = res.get("entity", "Unknown")
                score = res.get("final_score", 0)
                source = res.get("source", "unknown")
                print(f"     {i}. {entity} (score: {score:.3f}, source: {source})")

                # Show explanation
                explanation = graph_rag.explain_result(res, query)
                print(f"        {explanation}")

        # Show graph context
        if result.graph_context.get("relationships"):
            print("\n   Graph Relationships Found:")
            for rel in result.graph_context["relationships"][:3]:
                print(
                    f"     - {rel['subject']} --[{rel['relation']}]--> {rel['object']}",
                )


def demonstrate_subgraph_extraction(constructor: GraphConstructor):
    """Demonstrate subgraph extraction for visualization."""
    print("\n" + "=" * 60)
    print("4. SUBGRAPH EXTRACTION")
    print("=" * 60)

    graph_rag = GraphRAGQuery(constructor.get_graph())

    # Extract subgraphs for key entities
    entities = ["Acme Corporation", "Jane Doe"]

    for entity in entities:
        print(f"\n🕸️  Subgraph for '{entity}':")

        subgraph = graph_rag.get_entity_subgraph(entity, max_hops=2)

        if subgraph["found"]:
            print(f"   Nodes: {len(subgraph['nodes'])}")
            print(f"   Edges: {len(subgraph['edges'])}")

            # Show some nodes
            if subgraph["nodes"]:
                print("\n   Sample Nodes:")
                for node in subgraph["nodes"][:5]:
                    print(
                        f"     - {node['label']} ({node['type']})",
                    )

            # Show some edges
            if subgraph["edges"]:
                print("\n   Sample Edges:")
                for edge in subgraph["edges"][:5]:
                    src_label = next(
                        (n["label"] for n in subgraph["nodes"] if n["id"] == edge["source"]),
                        edge["source"],
                    )
                    tgt_label = next(
                        (n["label"] for n in subgraph["nodes"] if n["id"] == edge["target"]),
                        edge["target"],
                    )
                    print(
                        f"     - {src_label} --[{edge['relation']}]--> {tgt_label}",
                    )
        else:
            print("   ❌ Entity not found in graph")


async def demonstrate_hybrid_rag():
    """Demonstrate hybrid RAG with multiple strategies."""
    print("\n" + "=" * 60)
    print("5. HYBRID RAG STRATEGIES")
    print("=" * 60)

    # Build a simple graph
    graph_store = GraphStore()
    graph_store.add_node("person_1", "John Smith", node_type="PERSON")
    graph_store.add_node("org_1", "Acme Corp", node_type="ORG")
    graph_store.add_edge("person_1", "org_1", "works_at")

    # Initialize hybrid RAG (without real vector/BM25 stores for demo)
    hybrid_rag = HybridRAG(
        vector_store=None,
        bm25_index=None,
        graph_store=graph_store,
    )

    # Test different strategies
    query = "John Smith Acme"

    print(f"\n💬 Query: '{query}'")

    # Graph-only retrieval
    print("\n   📊 Strategy: Graph")
    try:
        results = await hybrid_rag.retrieve(query, strategy="graph", top_k=3)
        print(f"   Results: {len(results)}")
        for r in results[:3]:
            print(f"     - {r.get('entity', 'N/A')}")
    except Exception as e:
        print(f"   Note: {e}")

    print(
        "\n   ℹ️  Other strategies (dense, sparse, hybrid) require",
    )
    print("      vector store and BM25 index to be configured.")


def demonstrate_manual_triples(constructor: GraphConstructor):
    """Demonstrate manually adding knowledge triples."""
    print("\n" + "=" * 60)
    print("6. MANUAL TRIPLE ADDITION")
    print("=" * 60)

    print("\n➕ Adding manual triples...")

    # Add some custom triples
    triples = [
        ("John Smith", "specializes_in", "Corporate Law"),
        ("Acme Corporation", "industry", "Technology"),
        ("Jane Doe", "mentor_of", "John Smith"),
    ]

    for subject, relation, obj in triples:
        constructor.add_triple(
            subject,
            relation,
            obj,
            source="manual",
            confidence=1.0,
        )
        print(f"   Added: {subject} --[{relation}]--> {obj}")

    # Verify additions
    print("\n✅ Updated graph statistics:")
    stats = constructor.get_statistics()
    graph_stats = stats["graph_stats"]
    print(f"   Total Nodes: {graph_stats['num_nodes']}")
    print(f"   Total Edges: {graph_stats['num_edges']}")


def demonstrate_entity_merging(constructor: GraphConstructor):
    """Demonstrate entity resolution/merging."""
    print("\n" + "=" * 60)
    print("7. ENTITY RESOLUTION")
    print("=" * 60)

    print("\n🔗 Merging similar entities...")

    # These might be duplicates that need merging
    merge_pairs = [
        ("john smith", "John Smith"),  # Case variations
        ("acme corp.", "Acme Corporation"),  # Name variations
    ]

    for entity1, entity2 in merge_pairs:
        success = constructor.merge_entities(entity1, entity2)
        if success:
            print(f"   ✓ Merged '{entity1}' into '{entity2}'")
        else:
            print(f"   ℹ️  Could not merge '{entity1}' and '{entity2}'")


async def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH SYSTEM DEMONSTRATION")
    print("=" * 60)

    # 1. Build graph
    constructor = demonstrate_graph_construction()

    # 2. Entity context
    demonstrate_entity_context(constructor)

    # 3. Graph RAG
    await demonstrate_graph_rag(constructor)

    # 4. Subgraph extraction
    demonstrate_subgraph_extraction(constructor)

    # 5. Hybrid RAG
    await demonstrate_hybrid_rag()

    # 6. Manual triples
    demonstrate_manual_triples(constructor)

    # 7. Entity merging
    demonstrate_entity_merging(constructor)

    print("\n" + "=" * 60)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("  1. Knowledge graphs enable structured knowledge representation")
    print("  2. Graph-enhanced RAG improves retrieval with relational context")
    print("  3. Entity linking ensures consistency across documents")
    print("  4. Hybrid strategies combine multiple retrieval methods")
    print("  5. Subgraph extraction enables targeted context visualization")


if __name__ == "__main__":
    asyncio.run(main())
