# Phase 3: Hybrid RAG Pipeline - Implementation Plan

## 🎯 Objectives

Implement advanced RAG (Retrieval-Augmented Generation) capabilities with hybrid search, reranking, and intelligent document processing.

---

## 📊 Current State (Post-Phase 2)

### ✅ Available Infrastructure
- **Phase 0**: Semantic memory with pgvector (2000-dim embeddings, HNSW index)
- **Phase 2**: Redis caching layer with semantic similarity matching
- **Storage**: PostgreSQL + Supabase for vector search
- **Memory**: MemoryManager with episodic/semantic/working memory
- **MCP Servers**: GitHub, Context7, Markitdown, Playwright

### 🎯 Phase 3 Goals
1. **Hybrid Retrieval**: Dense (vector) + Sparse (BM25) search
2. **Advanced Reranking**: Cross-encoder models for precision
3. **Smart Chunking**: Contextual and semantic-aware chunking
4. **Document Processing**: PDF, DOCX, HTML, MD parsing with Markitdown MCP
5. **Integration**: Seamless integration with existing cache and memory layers

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│              User Query                              │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│          RAGPipelineAgent                            │
│  • Query analysis & expansion                        │
│  • Hybrid retrieval orchestration                    │
│  • Result fusion & ranking                           │
└─────────────────────────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │                            │
        ▼                            ▼
┌──────────────────┐      ┌──────────────────┐
│  Dense Retrieval │      │  Sparse Retrieval│
│  (Vector Search) │      │     (BM25)       │
│                  │      │                  │
│  • Supabase      │      │  • Rank-BM25     │
│  • pgvector      │      │  • TF-IDF        │
│  • HNSW index    │      │  • Inverted idx  │
└──────────────────┘      └──────────────────┘
        │                            │
        └─────────────┬──────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│          Reranker (Cross-Encoder)                    │
│  • BAAI/bge-reranker-base                            │
│  • Cohere rerank-multilingual                        │
│  • Precision-focused reordering                      │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│          LLM Response Generation                     │
│  • Context assembly                                  │
│  • Cache-aware generation                            │
│  • Streaming support                                 │
└─────────────────────────────────────────────────────┘
```

---

## 📦 Implementation Components

### 1. **RAGPipelineAgent** (Priority: HIGH)
**File**: `core/groupagents/rag_pipeline_agent.py`

**Features**:
- Query expansion & reformulation
- Hybrid retrieval (dense + sparse)
- Result fusion (Reciprocal Rank Fusion)
- Cross-encoder reranking
- Context window management

**Methods**:
```python
class RAGPipelineAgent:
    async def aretrieve(
        query: str,
        user_id: str,
        top_k: int = 10,
        rerank_top_k: int = 5,
        use_hybrid: bool = True
    ) -> List[Document]

    async def aembed_documents(texts: List[str]) -> List[List[float]]
    async def achunk(text: str, chunk_size: int = 512) -> List[str]
    async def aparse_file(file_path: str) -> str  # Uses Markitdown MCP
```

---

### 2. **Sparse Retrieval (BM25)**
**File**: `core/rag/sparse_retrieval.py`

**Dependencies**: `rank-bm25`

**Features**:
- BM25 Okapi implementation
- Inverted index building
- Fast keyword-based search
- Integration with dense retrieval

**Methods**:
```python
class BM25Retriever:
    def __init__(self, documents: List[str], tokenizer: Callable)
    async def asearch(query: str, top_k: int = 10) -> List[Tuple[str, float]]
    async def aupdate_index(new_docs: List[str])
```

---

### 3. **Cross-Encoder Reranker**
**File**: `core/rag/reranker.py`

**Models**:
- `BAAI/bge-reranker-base` (default)
- `BAAI/bge-reranker-large` (high quality)
- `Cohere/rerank-multilingual-v2.0` (API-based)

**Features**:
- Precision-optimized reranking
- Batch processing support
- Score normalization
- Fallback to simple scoring

**Methods**:
```python
class CrossEncoderReranker:
    async def arerank(
        query: str,
        documents: List[str],
        scores: List[float],
        top_k: int = 5
    ) -> List[Tuple[str, float]]
```

---

### 4. **Contextual Chunking**
**File**: `core/rag/chunking.py`

**Strategies**:
- **Fixed-size**: Simple character/token-based
- **Semantic**: Sentence/paragraph boundaries
- **Recursive**: Hierarchical chunking with overlap
- **Contextual**: Preserves document structure

**Features**:
- Overlap control
- Metadata preservation
- Chunk size optimization
- Language-aware splitting

**Methods**:
```python
class ContextualChunker:
    async def achunk_text(
        text: str,
        chunk_size: int = 512,
        overlap: int = 50,
        strategy: str = "semantic"
    ) -> List[Chunk]

    async def achunk_document(
        file_path: str,
        use_markitdown: bool = True
    ) -> List[Chunk]
```

---

### 5. **Document Parsing with Markitdown MCP**
**File**: `core/rag/document_parser.py`

**Features**:
- PDF → Markdown conversion
- DOCX → Markdown conversion
- HTML → Markdown conversion
- Image OCR (via Markitdown)
- Metadata extraction

**MCP Integration**:
```python
from mcp import use_tool

class DocumentParser:
    async def aparse_pdf(file_path: str) -> str:
        # Uses Markitdown MCP server
        result = await use_tool("markitdown", "convert", {
            "file_path": file_path,
            "output_format": "markdown"
        })
        return result

    async def aparse_docx(file_path: str) -> str:
        # Uses Markitdown MCP
        pass
```

---

### 6. **Hybrid Search Fusion**
**File**: `core/rag/fusion.py`

**Algorithm**: Reciprocal Rank Fusion (RRF)

**Formula**:
```
RRF_score(d) = Σ (1 / (k + rank_i(d)))
where:
  k = 60 (standard constant)
  rank_i(d) = rank of document d in retrieval method i
```

**Features**:
- Combines dense + sparse results
- Weight adjustment per source
- Deduplication
- Score normalization

---

### 7. **Integration with Existing Systems**

#### Cache Integration (Phase 2)
```python
from core.caching.semantic_cache import get_semantic_cache

class RAGPipelineAgent:
    async def aretrieve(self, query: str):
        # Check cache first
        cache = get_semantic_cache()
        cached = await cache.get(query)
        if cached:
            return cached

        # Retrieve + rerank
        results = await self._hybrid_retrieve(query)

        # Cache results
        await cache.set(query, results, ttl=3600)
        return results
```

#### Memory Integration (Phase 0/1)
```python
from core.memory.memory_manager_v2 import create_production_memory_manager

memory = create_production_memory_manager()

# Store retrieved documents in episodic memory
await memory.ainsert_episodic([
    {"source": "rag_retrieval", "action": "retrieved", "payload": doc}
    for doc in documents
])
```

---

## 🧪 Testing Strategy

### Unit Tests
**File**: `tests/unit/rag/test_rag_pipeline.py`

```python
async def test_hybrid_retrieval():
    agent = RAGPipelineAgent()
    results = await agent.aretrieve("contract law basics", top_k=10)
    assert len(results) > 0
    assert all(r.score > 0 for r in results)

async def test_bm25_search():
    retriever = BM25Retriever(documents)
    results = await retriever.asearch("immigration law", top_k=5)
    assert len(results) == 5

async def test_cross_encoder_reranking():
    reranker = CrossEncoderReranker()
    reranked = await reranker.arerank(query, docs, scores, top_k=3)
    assert reranked[0][1] > reranked[1][1]  # Scores descending
```

### Integration Tests
**File**: `tests/integration/rag/test_rag_integration.py`

```python
async def test_end_to_end_rag_pipeline():
    # Upload document
    parser = DocumentParser()
    text = await parser.aparse_pdf("test.pdf")

    # Chunk and index
    chunker = ContextualChunker()
    chunks = await chunker.achunk_text(text)

    # Retrieve
    agent = RAGPipelineAgent()
    results = await agent.aretrieve("find visa requirements")

    assert len(results) > 0
```

---

## 📊 Performance Targets

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| **Retrieval Latency** | < 100ms | TBD | Dense + Sparse + Rerank |
| **Precision@5** | > 0.85 | TBD | With reranker |
| **Recall@10** | > 0.90 | TBD | Hybrid search |
| **Cache Hit Rate** | > 60% | TBD | Semantic cache |
| **Document Processing** | < 2s/page | TBD | PDF/DOCX parsing |

---

## 📅 Timeline

### Week 1: Foundation (Dec 2-8)
- [x] Create Phase 3 plan
- [ ] Implement BM25 sparse retrieval
- [ ] Create basic RAGPipelineAgent structure
- [ ] Add unit tests for sparse retrieval

### Week 2: Hybrid Search (Dec 9-15)
- [ ] Implement hybrid fusion (RRF)
- [ ] Add cross-encoder reranking
- [ ] Integrate with existing vector search
- [ ] Test hybrid retrieval accuracy

### Week 3: Document Processing (Dec 16-22)
- [ ] Integrate Markitdown MCP for parsing
- [ ] Implement contextual chunking
- [ ] Add support for PDF/DOCX/HTML
- [ ] Create document ingestion pipeline

### Week 4: Integration & Testing (Dec 23-29)
- [ ] Integrate with Phase 2 caching
- [ ] Integrate with Phase 0/1 memory
- [ ] End-to-end integration tests
- [ ] Performance optimization
- [ ] Documentation

---

## 🛠️ Dependencies

### New Python Packages
```txt
# Sparse retrieval
rank-bm25==0.2.2

# Reranking
sentence-transformers==2.2.2

# Document processing (via MCP)
# No direct dependency - uses Markitdown MCP server

# Tokenization
tiktoken==0.5.1
```

### MCP Servers (Already Installed)
- ✅ **Markitdown**: Document conversion (PDF, DOCX, HTML → Markdown)
- ✅ **Context7**: Documentation lookup
- ✅ **GitHub**: Code access
- ✅ **Playwright**: Web scraping (if needed)

---

## 🔧 Configuration

### Environment Variables
```bash
# RAG Configuration
RAG_HYBRID_ENABLED=true
RAG_DENSE_WEIGHT=0.6
RAG_SPARSE_WEIGHT=0.4
RAG_RERANK_MODEL=BAAI/bge-reranker-base
RAG_RERANK_TOP_K=5
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=50

# Document Processing
RAG_USE_MARKITDOWN_MCP=true
RAG_SUPPORTED_FORMATS=pdf,docx,html,md,txt
```

---

## 🎯 Success Criteria

### Functional
- [ ] Hybrid retrieval works (dense + sparse)
- [ ] Reranking improves precision by >20%
- [ ] Document parsing supports PDF/DOCX/HTML
- [ ] Cache integration reduces latency by >50%
- [ ] All tests passing (unit + integration)

### Non-Functional
- [ ] Latency < 100ms for cached queries
- [ ] Latency < 500ms for uncached queries
- [ ] Support 1000+ documents without degradation
- [ ] Memory usage < 2GB per process
- [ ] CPU usage < 80% under load

---

## 📚 Documentation Deliverables

1. **Technical Documentation**: `PHASE_3_RAG_PIPELINE.md`
2. **API Documentation**: Docstrings for all public methods
3. **Usage Examples**: `examples/rag_pipeline_example.py`
4. **Integration Guide**: How to integrate with existing code
5. **Troubleshooting**: Common issues and solutions

---

## 🚀 Next Steps After Phase 3

1. **Context Engineering** (Phase 4)
   - Adaptive context building
   - Context compression techniques
   - Agent-specific templates

2. **Self-Correcting Agents** (Phase 5)
   - Validation loops
   - Confidence scoring
   - Auto-correction mechanisms

3. **Advanced Query Optimization** (Phase 6)
   - Query understanding
   - Intent classification
   - Multi-turn conversation support

---

**Status**: 📝 Planning Complete - Ready for Implementation
**Priority**: 🔴 HIGH
**Estimated Duration**: 4 weeks
**Dependencies**: Phase 0, Phase 2
**Owner**: Claude Code + MCP Servers Integration
