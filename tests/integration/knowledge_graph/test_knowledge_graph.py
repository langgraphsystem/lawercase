"""Integration tests for Knowledge Graph system."""

from __future__ import annotations

import pytest

from core.knowledge_graph import (EntityExtractor, GraphConstructor,
                                  GraphRAGQuery, GraphStore, HybridRAG,
                                  KnowledgeTriple, RelationExtractor)


@pytest.fixture
def graph_store():
    """Create a graph store for testing."""
    return GraphStore()


@pytest.fixture
def sample_graph(graph_store):
    """Create a sample graph with test data."""
    # Add nodes
    graph_store.add_node("person_1", "John Doe", node_type="PERSON")
    graph_store.add_node("person_2", "Jane Smith", node_type="PERSON")
    graph_store.add_node("org_1", "Acme Corp.", node_type="ORG")
    graph_store.add_node("org_2", "Tech Inc.", node_type="ORG")

    # Add edges
    graph_store.add_edge("person_1", "org_1", "works_at")
    graph_store.add_edge("person_2", "org_2", "works_at")
    graph_store.add_edge("person_1", "person_2", "knows")
    graph_store.add_edge("org_1", "org_2", "partner_of")

    return graph_store


class TestGraphStore:
    """Test GraphStore functionality."""

    def test_add_and_get_node(self, graph_store):
        """Test adding and retrieving nodes."""
        graph_store.add_node("test_1", "Test Entity", node_type="TEST")

        node = graph_store.get_node("test_1")
        assert node is not None
        assert node["label"] == "Test Entity"
        assert node["node_type"] == "TEST"

    def test_add_and_get_edge(self, graph_store):
        """Test adding and retrieving edges."""
        graph_store.add_node("n1", "Node 1")
        graph_store.add_node("n2", "Node 2")
        graph_store.add_edge("n1", "n2", "test_relation", weight=0.8)

        edges = graph_store.get_edges("n1", "n2")
        assert len(edges) > 0
        assert any(e["relation"] == "test_relation" for e in edges)

    def test_get_neighbors(self, sample_graph):
        """Test neighbor retrieval."""
        neighbors = sample_graph.get_neighbors("person_1")
        assert "org_1" in neighbors
        assert "person_2" in neighbors

    def test_get_neighbors_by_relation(self, sample_graph):
        """Test filtered neighbor retrieval."""
        neighbors = sample_graph.get_neighbors("person_1", relation="works_at")
        assert len(neighbors) == 1
        assert "org_1" in neighbors

    def test_get_paths(self, sample_graph):
        """Test path finding."""
        paths = sample_graph.get_paths("person_1", "org_2", max_length=3)
        assert len(paths) > 0

        # Should find path through person_2
        path_nodes = [node for path in paths for node in path]
        assert "person_2" in path_nodes or "org_1" in path_nodes

    def test_find_nodes_by_type(self, sample_graph):
        """Test node type filtering."""
        persons = sample_graph.find_nodes_by_type("PERSON")
        assert len(persons) == 2
        assert "person_1" in persons
        assert "person_2" in persons

    def test_find_nodes_by_pattern(self, sample_graph):
        """Test pattern-based search."""
        results = sample_graph.find_nodes_by_pattern(
            node_type="PERSON",
            label_contains="John",
        )
        assert len(results) == 1
        assert results[0] == "person_1"

    def test_get_related_entities(self, sample_graph):
        """Test related entity discovery."""
        related = sample_graph.get_related_entities("person_1", max_hops=2)

        # Should find direct neighbors (1 hop)
        assert "org_1" in related
        assert related["org_1"] == 1

        # Should find 2-hop neighbors
        assert "org_2" in related or "person_2" in related

    def test_get_subgraph(self, sample_graph):
        """Test subgraph extraction."""
        subgraph = sample_graph.get_subgraph(["person_1"], max_hops=1)

        assert subgraph.number_of_nodes() >= 2
        assert "person_1" in subgraph.nodes()

    def test_statistics(self, sample_graph):
        """Test graph statistics."""
        stats = sample_graph.get_stats()

        assert stats["num_nodes"] == 4
        assert stats["num_edges"] == 4
        assert stats["density"] > 0

    def test_to_dict(self, sample_graph):
        """Test graph serialization."""
        data = sample_graph.to_dict()

        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 4
        assert len(data["edges"]) == 4


class TestEntityExtractor:
    """Test EntityExtractor."""

    def test_extract_person_names(self):
        """Test person name extraction."""
        extractor = EntityExtractor()
        text = "John Doe and Jane Smith discussed the case."

        entities = extractor.extract(text)

        persons = [e for e in entities if e["type"] == "PERSON"]
        assert len(persons) >= 2

        person_texts = [e["text"] for e in persons]
        assert "John Doe" in person_texts
        assert "Jane Smith" in person_texts

    def test_extract_organizations(self):
        """Test organization extraction."""
        extractor = EntityExtractor()
        text = "Acme Corporation Inc. and Tech Solutions LLC."

        entities = extractor.extract(text)

        orgs = [e for e in entities if e["type"] == "ORG"]
        assert len(orgs) >= 1

    def test_extract_dates(self):
        """Test date extraction."""
        extractor = EntityExtractor()
        text = "The meeting was on 2024-01-15 and 01/20/2024."

        entities = extractor.extract(text)

        dates = [e for e in entities if e["type"] == "DATE"]
        assert len(dates) == 2

    def test_extract_money(self):
        """Test money extraction."""
        extractor = EntityExtractor()
        text = "The settlement was $1,000,000.00 and fees were $5,500."

        entities = extractor.extract(text)

        money = [e for e in entities if e["type"] == "MONEY"]
        assert len(money) == 2


class TestRelationExtractor:
    """Test RelationExtractor."""

    def test_extract_works_at(self):
        """Test 'works at' relation extraction."""
        extractor = RelationExtractor()
        text = "John Doe works at Acme Corporation."

        relations = extractor.extract(text, [])

        assert len(relations) > 0
        assert any(r.relation == "works_at" for r in relations)

    def test_extract_founded(self):
        """Test 'founded' relation extraction."""
        extractor = RelationExtractor()
        text = "Steve Jobs founded Apple Inc."

        relations = extractor.extract(text, [])

        founded_rels = [r for r in relations if r.relation == "founded"]
        assert len(founded_rels) > 0

    def test_extract_multiple_relations(self):
        """Test multiple relation extraction."""
        extractor = RelationExtractor()
        text = "John works at Acme Corp. Jane founded Tech LLC."

        relations = extractor.extract(text, [])

        assert len(relations) >= 2


class TestGraphConstructor:
    """Test GraphConstructor."""

    def test_add_document(self):
        """Test document processing."""
        constructor = GraphConstructor()
        text = "John Doe works at Acme Corporation Inc."

        result = constructor.add_document(text, doc_id="test_doc")

        assert result["entities_found"] >= 2
        assert result["nodes_added"] >= 2

    def test_entity_linking(self):
        """Test entity linking across documents."""
        constructor = GraphConstructor()

        doc1 = "John Doe works at Acme Corporation."
        doc2 = "John Doe graduated from Harvard."

        constructor.add_document(doc1, doc_id="doc1")
        constructor.add_document(doc2, doc_id="doc2")

        # "John Doe" should be linked to same entity
        context = constructor.get_entity_context("John Doe")

        assert context["found"]
        assert context["node_info"] is not None

    def test_add_triple_manually(self):
        """Test manual triple addition."""
        constructor = GraphConstructor()

        constructor.add_triple(
            "Alice",
            "knows",
            "Bob",
            source="manual",
        )

        graph = constructor.get_graph()
        assert graph.graph.number_of_edges() >= 1

    def test_get_entity_context(self):
        """Test entity context retrieval."""
        constructor = GraphConstructor()
        constructor.add_document("John Doe works at Acme Corp.")

        context = constructor.get_entity_context("John Doe", max_hops=2)

        assert context["found"]
        assert context["entity_id"] is not None

    def test_merge_entities(self):
        """Test entity merging."""
        constructor = GraphConstructor()

        # Create duplicate entities
        constructor.add_triple("John", "works_at", "Acme")
        constructor.add_triple("john", "knows", "Jane")

        # Merge them
        success = constructor.merge_entities("john", "John")

        assert success

    def test_statistics(self):
        """Test graph statistics."""
        constructor = GraphConstructor()
        constructor.add_document("John Doe works at Acme Corporation Inc.")

        stats = constructor.get_statistics()

        assert "graph_stats" in stats
        assert "cached_entities" in stats
        assert "entity_types" in stats


class TestGraphRAGQuery:
    """Test GraphRAGQuery."""

    @pytest.mark.asyncio
    async def test_query_basic(self, sample_graph):
        """Test basic graph RAG query."""
        rag = GraphRAGQuery(sample_graph)

        result = await rag.query("John Doe", top_k=5)

        assert result.query == "John Doe"
        assert result.graph_context is not None

    @pytest.mark.asyncio
    async def test_query_expansion(self, sample_graph):
        """Test query expansion with graph."""
        rag = GraphRAGQuery(sample_graph)

        result = await rag.query("John Doe", expand_hops=2, top_k=10)

        # Should find related entities
        assert len(result.graph_expanded) > 0

    @pytest.mark.asyncio
    async def test_reranking(self, sample_graph):
        """Test result reranking."""
        rag = GraphRAGQuery(sample_graph)

        result = await rag.query("John", rerank=True, top_k=5)

        # Results should have final scores
        if result.reranked_results:
            assert "final_score" in result.reranked_results[0]

    def test_get_entity_subgraph(self, sample_graph):
        """Test entity subgraph extraction."""
        rag = GraphRAGQuery(sample_graph)

        subgraph = rag.get_entity_subgraph("John Doe", max_hops=1)

        assert subgraph["found"]
        assert len(subgraph["nodes"]) > 0
        assert len(subgraph["edges"]) > 0

    def test_explain_result(self, sample_graph):
        """Test result explanation."""
        rag = GraphRAGQuery(sample_graph)

        result = {
            "source": "graph",
            "base_score": 0.8,
            "graph_boost": 0.1,
            "final_score": 0.9,
            "source_entity": "John Doe",
            "hops": 1,
        }

        explanation = rag.explain_result(result, "test query")

        assert "graph" in explanation.lower()
        assert "0.9" in explanation or "0.90" in explanation


class TestHybridRAG:
    """Test HybridRAG."""

    @pytest.mark.asyncio
    async def test_graph_strategy(self, sample_graph):
        """Test graph retrieval strategy."""
        hybrid = HybridRAG(graph_store=sample_graph)

        results = await hybrid.retrieve("John", strategy="graph", top_k=5)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_invalid_strategy(self, sample_graph):
        """Test invalid strategy handling."""
        hybrid = HybridRAG(graph_store=sample_graph)

        with pytest.raises(ValueError):
            await hybrid.retrieve("test", strategy="invalid")


class TestKnowledgeTriple:
    """Test KnowledgeTriple model."""

    def test_to_dict(self):
        """Test triple serialization."""
        triple = KnowledgeTriple(
            subject="Alice",
            relation="knows",
            obj="Bob",
            metadata={"source": "test"},
            confidence=0.9,
        )

        data = triple.to_dict()

        assert data["subject"] == "Alice"
        assert data["relation"] == "knows"
        assert data["object"] == "Bob"
        assert data["confidence"] == 0.9
        assert data["metadata"]["source"] == "test"
