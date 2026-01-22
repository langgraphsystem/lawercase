# MegaAgent Pro API Reference

> Comprehensive API documentation for the MegaAgent Pro EB-1A petition assistant.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Core Agents API](#core-agents-api)
4. [Services API](#services-api)
5. [Memory System](#memory-system)
6. [RAG Pipeline](#rag-pipeline)
7. [MCP Integration](#mcp-integration)
8. [Workflows](#workflows)
9. [Error Handling](#error-handling)

---

## Overview

MegaAgent Pro provides a multi-agent system for EB-1A visa petition preparation. The system uses:

- **LangGraph** for workflow orchestration
- **Hybrid RAG** for document retrieval
- **MCP (Model Context Protocol)** for tool integration
- **Multi-LLM routing** for cost optimization

### Base URL

```
Production: https://api.megaagent.pro/v1
Development: http://localhost:8000/v1
```

### Response Format

All responses follow a standard format:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "req_xxx",
    "timestamp": "2025-01-18T12:00:00Z",
    "latency_ms": 150
  }
}
```

---

## Authentication

### JWT Authentication

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "..."
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### API Key Authentication

Include the API key in the header:
```http
Authorization: Bearer sk_live_xxxx
```

---

## Core Agents API

### MegaAgent (Central Orchestrator)

The central agent that routes commands to specialized agents.

```python
from core.groupagents import MegaAgent

agent = MegaAgent(memory_manager=memory)

# Handle a command
response = await agent.handle_command(
    command="/ask",
    payload={"question": "What are EB-1A requirements?"},
    user_id="user-123",
    thread_id="thread-456",
)
```

#### Available Commands

| Command | Description | Payload |
|---------|-------------|---------|
| `/ask` | Answer questions about EB-1A | `{"question": str}` |
| `/train` | Train on new documents | `{"documents": list}` |
| `/validate` | Validate petition | `{"document_id": str}` |
| `/generate` | Generate documents | `{"type": str, "case_id": str}` |

### CaseAgent

Manages case CRUD operations with optimistic locking.

```python
from core.groupagents import CaseAgent

agent = CaseAgent(memory_manager=memory)

# Create a case
case = await agent.acreate_case(
    user_id="user-123",
    case_data={
        "beneficiary_name": "John Doe",
        "type": "eb1a",
        "criteria": ["awards", "publications", "original_contribution"],
    }
)

# Get a case
case = await agent.aget_case(case_id="case-123", user_id="user-123")

# Update a case
case = await agent.aupdate_case(
    case_id="case-123",
    updates={"status": "in_progress"},
    user_id="user-123",
)

# Search cases
cases = await agent.asearch_cases(
    query=CaseQuery(status="active", type="eb1a"),
    user_id="user-123",
)
```

### WriterAgent

Generates legal documents with template support.

```python
from core.groupagents import WriterAgent

agent = WriterAgent(memory_manager=memory)

# Generate petition letter
result = await agent.agenerate_letter(
    case_id="case-123",
    letter_type="petition",
    template="eb1a_standard",
    context={"beneficiary": {...}, "evidence": [...]},
)

# Generate PDF
pdf_bytes = await agent.agenerate_document_pdf(
    content=result.content,
    template="professional",
)
```

### ValidatorAgent

Validates documents with self-correction.

```python
from core.groupagents import ValidatorAgent, ValidationRequest, ValidationLevel

agent = ValidatorAgent(memory_manager=memory)

# Validate a document
result = await agent.avalidate(
    ValidationRequest(
        document_id="doc-123",
        content="...",
        document_type="petition_letter",
        validation_level=ValidationLevel.STRICT,
        user_id="user-123",
    )
)

print(f"Valid: {result.is_valid}")
print(f"Score: {result.score}")
print(f"Issues: {result.issues}")
```

### RAGPipelineAgent

Hybrid retrieval with context enrichment.

```python
from core.groupagents import RAGPipelineAgent

agent = RAGPipelineAgent(memory_manager=memory)

# Query with RAG
answer = await agent.arag(
    query="What evidence supports the awards criterion?",
    case_id="case-123",
    top_k=5,
)

print(f"Answer: {answer.answer}")
print(f"Sources: {answer.sources}")
print(f"Confidence: {answer.confidence}")

# Search similar cases
similar = await agent.asearch_similar_cases(
    case_id="case-123",
    top_k=3,
)
```

---

## Services API

### Evidence Classifier

AI-powered evidence classification for EB-1A criteria.

```python
from core.services import EvidenceClassifier, EB1ACriterion

classifier = EvidenceClassifier()

# Classify a document
result = await classifier.classify_document(
    document_id="doc-123",
    content="This is a letter from the National Science Foundation...",
    filename="nsf_letter.pdf",
)

print(f"Primary criterion: {result.primary_criterion}")
print(f"Strength: {result.strength}")
print(f"Confidence: {result.confidence}")

# Assess case evidence
assessment = await classifier.assess_case_evidence(
    case_id="case-123",
    classifications=[...],
)

print(f"Overall strength: {assessment.overall_strength}")
print(f"Criteria met: {assessment.criteria_met}")
print(f"Recommendations: {assessment.recommendations}")
```

### RFE Analyzer

Analyzes RFE risk patterns and provides remediation.

```python
from core.services import RFEAnalyzer

analyzer = RFEAnalyzer()

# Analyze case risk
assessment = analyzer.analyze_case(
    case_id="case-123",
    evidence_assessment=evidence_assessment,
    documents=documents,
)

print(f"Risk level: {assessment.risk_level}")
print(f"Issues: {assessment.issues}")
print(f"Recommendations: {assessment.recommendations}")

# Get remediation guide
guide = analyzer.get_remediation_guide(
    issue_type=RFEIssueType.AWARDS_NOT_NATIONALLY_RECOGNIZED
)
```

### Document Consistency Checker

Cross-references all petition documents for consistency.

```python
from core.services import DocumentConsistencyChecker

checker = DocumentConsistencyChecker()

# Check case consistency
result = await checker.check_case_consistency(
    case_id="case-123",
    petition_letter=petition_text,
    exhibits=[
        {"id": "A", "content": "..."},
        {"id": "B", "content": "..."},
    ],
    beneficiary_info={"name": "John Doe", "dob": "1990-01-01"},
)

print(f"Consistent: {result.is_consistent}")
print(f"Score: {result.consistency_score}")
print(f"Critical issues: {result.critical_count}")

for issue in result.issues:
    print(f"  [{issue['severity']}] {issue['description']}")
```

---

## Memory System

### Agentic Memory (A-Mem)

Modern memory system with temporal decay and knowledge graphs.

```python
from core.memory import AgenticMemory, MemoryType

memory = AgenticMemory()

# Add a memory note
note = await memory.add(
    content="Beneficiary received IEEE Best Paper Award in 2024",
    memory_type=MemoryType.EPISODIC,
    tags=["award", "ieee"],
    case_id="case-123",
    importance=0.9,
)

# Retrieve relevant memories
memories = await memory.retrieve(
    query="What awards has the beneficiary received?",
    memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC],
    top_k=5,
)

# Add entity to knowledge graph
entity = await memory.add_entity(
    name="IEEE",
    entity_type="organization",
    attributes={"field": "engineering", "type": "professional_society"},
)

# Add relationship
relation = await memory.add_relation(
    source_id=beneficiary_id,
    target_id=entity.node_id,
    relation_type="member_of",
)

# Consolidate memories (merge similar, decay old)
consolidated = await memory.consolidate(case_id="case-123")
```

### Memory Manager

Central interface for all memory operations.

```python
from core.memory import MemoryManager

manager = MemoryManager()

# Write audit event
await manager.alog_audit(audit_event)

# Retrieve with context
records = await manager.aretrieve(
    query="EB-1A awards evidence",
    user_id="user-123",
)
```

---

## RAG Pipeline

### Hybrid RAG with GraphRAG

```python
from core.rag import (
    RAGPipeline,
    GraphRAG,
    NodeType,
    RelationType,
)

# Traditional RAG
rag = RAGPipeline()
result = await rag.query("What are the requirements?")

# Graph RAG
graph_rag = GraphRAG()

# Add nodes
beneficiary = await graph_rag.add_node(
    node_type=NodeType.BENEFICIARY,
    name="John Doe",
    properties={"field": "AI"},
)

# Search graph
results = await graph_rag.search(
    GraphQuery(
        start_query="AI research achievements",
        max_hops=2,
        node_types=[NodeType.AWARD, NodeType.PUBLICATION],
    )
)

# Generate context
context = await graph_rag.generate_context(
    query="What publications does the beneficiary have?",
    case_id="case-123",
)
```

---

## MCP Integration

### Tool Search (Dynamic Loading)

```python
from core.mcp import MCPToolSearch, ToolCategory

search = MCPToolSearch()

# Register server tools
await search.register_server_tools("filesystem", fs_tools)
await search.register_server_tools("github", github_tools)

# Search for tools
results = await search.search_tools(
    query="read files and search code",
    categories=[ToolCategory.FILE_SYSTEM, ToolCategory.CODE],
    max_results=5,
)

# Get recommendations
recommendation = await search.recommend_tools(
    task="Analyze repository structure",
    context_limit=8000,
)

# Load selected tools
tools = await search.load_tools([r.tool_id for r in results])
```

---

## Workflows

### EB-1A Complete Workflow

```python
from core.orchestration.workflow_graph import build_eb1a_complete_workflow
from langgraph.checkpoint.memory import MemorySaver

# Build workflow
graph = build_eb1a_complete_workflow(memory_manager)
workflow = graph.compile(checkpointer=MemorySaver())

# Run workflow
result = await workflow.ainvoke(
    WorkflowState(
        thread_id="workflow-123",
        user_id="user-123",
        case_id="case-123",
        case_data={
            "criteria": ["awards", "publications"],
            "evidence": [...],
        },
    )
)

print(f"Final output: {result.final_output}")
```

### Human-in-the-Loop

```python
from core.orchestration.human_in_loop import (
    HumanInLoopManager,
    InterruptType,
    create_approval_interrupt,
    interrupt,
)

manager = HumanInLoopManager()

# In workflow node
async def approval_node(state):
    context = await manager.create_interrupt(
        interrupt_type=InterruptType.APPROVAL_REQUIRED,
        workflow_id=state.thread_id,
        title="Review Petition",
        data={"petition": state.petition_content},
    )

    response = interrupt(context)

    if response.response == "approved":
        return Command(goto="finalize")
    return Command(goto="revise")
```

---

## Error Handling

### Exception Types

```python
from core.exceptions import (
    ValidationError,
    WorkflowError,
    ConfigurationError,
    ResourceNotFoundError,
)

try:
    result = await agent.process(...)
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Field: {e.field}")
except WorkflowError as e:
    print(f"Workflow error: {e.workflow_name}")
    print(f"Details: {e.details}")
except ConfigurationError as e:
    print(f"Configuration error: {e.message}")
```

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid case data",
    "details": {
      "field": "beneficiary_name",
      "reason": "Required field missing"
    }
  },
  "meta": {
    "request_id": "req_xxx",
    "timestamp": "2025-01-18T12:00:00Z"
  }
}
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/*` | 10 | 1 minute |
| `/cases/*` | 100 | 1 minute |
| `/documents/*` | 50 | 1 minute |
| `/generate/*` | 20 | 1 minute |
| `/validate/*` | 30 | 1 minute |

---

## Webhooks

### Configure Webhooks

```http
POST /webhooks
Content-Type: application/json
Authorization: Bearer <token>

{
  "url": "https://your-server.com/webhook",
  "events": ["case.created", "case.updated", "document.generated"],
  "webhook_key": "whsec_REPLACE_WITH_YOUR_KEY"
}
```

### Webhook Events

| Event | Description |
|-------|-------------|
| `case.created` | New case created |
| `case.updated` | Case updated |
| `case.status_changed` | Case status changed |
| `document.generated` | Document generated |
| `validation.completed` | Validation completed |
| `workflow.completed` | Workflow completed |
| `workflow.requires_approval` | Human approval needed |

---

## SDKs

### Python SDK

```bash
pip install megaagent-sdk
```

```python
from megaagent import MegaAgentClient

client = MegaAgentClient(api_key=os.environ["MEGAAGENT_API_KEY"])

# Create case
case = await client.cases.create(
    beneficiary_name="John Doe",
    type="eb1a",
)

# Generate petition
petition = await client.documents.generate_petition(case_id=case.id)
```

### JavaScript/TypeScript SDK

```bash
npm install @megaagent/sdk
```

```typescript
import { MegaAgentClient } from '@megaagent/sdk';

const client = new MegaAgentClient({ apiKey: process.env.MEGAAGENT_API_KEY });

// Create case
const case = await client.cases.create({
  beneficiaryName: 'John Doe',
  type: 'eb1a',
});
```

---

## Changelog

### v0.2.0 (2025-01-18)
- Added GraphRAG for knowledge graphs
- Added MCP Tool Search for dynamic loading
- Added Document Consistency Checker
- Added A-Mem (Agentic Memory) system
- Added LangGraph 1.0 interrupt/Command features
- Added Evidence Classifier
- Added RFE Pattern Analyzer

### v0.1.0 (2025-01-01)
- Initial release
- Core agents (MegaAgent, CaseAgent, WriterAgent, ValidatorAgent)
- Hybrid RAG pipeline
- Basic workflow support

---

*Last updated: 2025-01-18*
