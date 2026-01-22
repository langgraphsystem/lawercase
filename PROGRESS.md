# PDF Package Generator - Progress

## Completed Tasks

### 1. PDF Form Filling (USCIS Forms)
- **File**: `core/services/uscis_forms.py`
- Added functions to fill USCIS forms using pymupdf (fitz):
  - `fill_g1145_pdf()` - e-Notification form
  - `fill_i140_pdf()` - Immigrant Petition (EB-1A self-petition, E11)
  - `fill_i907_pdf()` - Premium Processing
  - `fill_g28_pdf()` - Attorney Appearance

### 2. PDF Package Generator Updates
- **File**: `core/services/pdf_package_generator.py`
- Updated to use new PDF filling functions
- Changed header styling: font 11pt, line 2px

### 3. Chrome PDF Generation Test
- **File**: `test_puppeteer_pdf.py`
- Uses Playwright + Chromium for PDF generation
- Generates cover page matching LaTeX style
- Output: `output/pdf_packages/chrome_test/cover_page_latex_style.pdf`

### 4. LaTeX PDF Generation (COMPLETED 2025-12-05)
- **Status**: FULLY INTEGRATED
- **MiKTeX**: Installed at `C:\Program Files\MiKTeX\miktex\bin\x64\`
- **Auto-install**: Enabled via `initexmf --set-config-value [MPM]AutoInstall=1`

#### LaTeX Templates Created (`core/templates/latex/`):
| Template | Description |
|----------|-------------|
| `cover_page.tex` | Table of Contents with running header |
| `petition_letter.tex` | Full petition with all 9 criteria sections |
| `statement_of_intent.tex` | Statement of intent to work in US |
| `exhibits_list.tex` | List of exhibits with longtable |
| `passport_page.tex` | Passport placeholder with tikz boxes |

#### LaTeX Generator (`core/services/latex_generator.py`):
```python
from core.services.latex_generator import LaTeXGenerator

generator = LaTeXGenerator()

# Generate individual documents:
generator.generate_cover_page(output_path, name, include_premium=True, page_info={...})
generator.generate_petition_letter(output_path, name, field, sections={...})
generator.generate_statement_of_intent(output_path, name, field)
generator.generate_exhibits_list(output_path, name, exhibits=[...])
generator.generate_passport_page(output_path, name, passport_number)
```

#### PDF Package Generator (`core/services/pdf_package_generator.py`):
- Now uses LaTeX for all document generation (not Playwright)
- Async methods with `run_in_executor` for non-blocking

```python
from core.services.pdf_package_generator import generate_pdf_package

result = generate_pdf_package(
    case_id="case-001",
    case_data={"field": "Computer Science"},
    user_data={"full_name": "Ivan Petrov", "passport_number": "AB123456"},
    petition_sections={"summary": "...", "awards": "..."},
    exhibits=[{"number": 1, "title": "Resume", "page": 93}],
    include_premium=True,
    include_attorney=False
)
# Returns: output/pdf_packages/case-001/case-001_complete_package.pdf
```

## Reference Files
- `primer/first.pdf` - LaTeX reference (Table of Contents page)
- `primer/inkin.pdf` - Full petition (~300MB)
- `primer/first.xml` - Structure exported from Adobe Acrobat

## Key Info
- Reference PDF created with: **LaTeX with hyperref** + **pdfTeX-1.40.25**
- Current: **MiKTeX 25.4** (pdfTeX 4.21)
- Target: Generate identical PDF using LaTeX - ACHIEVED

## Commands

```bash
# Check LaTeX installation
"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe" --version

# Test all LaTeX templates
python -c "from core.services.latex_generator import test_latex; test_latex()"

# Test full PDF package generation
python -c "from core.services.pdf_package_generator import test_package_generation; test_package_generation()"

# Generate package for a real case (in Python):
from core.services.pdf_package_generator import generate_pdf_package
generate_pdf_package(case_id="my-case", case_data={...}, user_data={...})
```

## Output Directories
- `output/pdf_packages/latex_test/` - Individual template tests
- `output/pdf_packages/{case_id}/` - Generated packages per case

---

### 5. Intake Questionnaire System (UPDATED 2025-12-05)

#### Architecture
```
User Message → Telegram Handler → Validation → Fact Synthesis → Semantic Memory
```

#### Files Structure
| File | Purpose |
|------|---------|
| `core/intake/schema.py` | 11 блоков вопросов (Pydantic models) |
| `core/intake/career_intake.py` | Детальный опрос по карьере (company-by-company) |
| `core/intake/synthesis.py` | Синтез фактов из Q&A для памяти |
| `core/intake/validation.py` | Валидация ответов по типам |
| `telegram_interface/handlers/intake_handlers.py` | Telegram handlers для основного опроса |
| `telegram_interface/handlers/career_intake_handlers.py` | Handlers для детального career intake |

#### 11 Blocks
1. `basic_info` - Общая информация (8 вопросов + документы)
2. `family_childhood` - Семья и детство (4 вопроса)
3. `school` - Школа (9 вопросов + документы)
4. `university` - Университет (10 вопросов + документы)
5. **`career`** - Профессиональный путь → **TRIGGERS DETAILED INTAKE**
6. `projects_research` - Проекты/Публикации (7 вопросов + документы)
7. `awards` - Награды (4 вопроса + документы)
8. `talks_public_activity` - Конференции/Выступления (5 вопросов)
9. `courses_certificates` - Курсы/Сертификаты (2 вопроса)
10. `recommenders` - Рекомендатели (2 вопроса)
11. `goals_usa` - Цели в США (3 вопроса)

#### Career Intake Integration (NEW)
When main intake reaches block 5 (`career`), it automatically triggers detailed career intake:

```
Main Intake → Block 5 (career) → _start_detailed_career_intake()
                                        ↓
                                 Career Intake Flow
                                 (company by company)
                                        ↓
                                 _complete_career_intake()
                                        ↓
                                 continue_intake_after_career()
                                        ↓
                                 Main Intake → Block 6 (projects_research)
```

**Career Intake Phases (per company):**
| Phase | Questions |
|-------|-----------|
| `company_count` | Сколько компаний в карьере |
| `company_basics` | Название, тип, сфера, локация, даты |
| `positions` | Должности, обязанности, управление |
| `projects` | Проекты, роль, результаты |
| `achievements` | Достижения, метрики, награды |
| `achievements_government` | Участие в законодательстве (для госслужбы) |
| `recommenders` | ФИО, должность, что может подтвердить |
| `evidence` | Загрузка документов |
| `company_summary` | Дополнительная информация |

**LLM Follow-up:** После ответов генерируются дополнительные вопросы на основе EB-1A критериев.

#### Storage
- **Answers** → Semantic Memory (MemoryRecord с tags и metadata)
- **Documents** → Document Storage (Supabase/R2/local) + OCR → Memory
- **Career data** → Structured CareerEntry objects → Memory

#### Telegram Commands
```
/intake_start   - Начать полный опрос (все 11 блоков)
/intake_status  - Статус прогресса
/intake_resume  - Продолжить
/intake_cancel  - Отменить

# Career-specific (можно запустить отдельно):
/career_start   - Детальный опрос по карьере
/career_status  - Статус career intake
/career_skip    - Пропустить фазу
/career_cancel  - Отменить career intake
```

#### Code Example
```python
# Main intake automatically handles everything:
# User: /intake_start
# Bot asks questions block by block
# At block 5 (career) → detailed career intake starts
# After career complete → continues with block 6
# At the end → all data in semantic memory

# To query collected data:
from core.memory.models import MemoryRecord
records = await memory.aquery(
    query="карьера достижения",
    case_id=case_id,
    tags=["career", "achievements"]
)
```

---

### 6. Questionnaire Improvements (UPDATED 2025-12-05)

#### Research Conducted
- EB-1A 10 criteria requirements from USCIS
- Two-tier adjudication process (regulatory criteria + final merits determination)
- Common RFE reasons and mistakes
- Best practices for evidence documentation

#### EB-1A 10 Criteria Coverage

| Criterion | Description | Block | Status |
|-----------|-------------|-------|--------|
| 1 | Awards for excellence | `awards` | ✅ Enhanced |
| 2 | Membership in associations | `talks_public_activity` | ✅ Added |
| 3 | Published material ABOUT applicant | `talks_public_activity` | ✅ Added |
| 4 | Judging work of others | `talks_public_activity` | ✅ Enhanced |
| 5 | Original contributions | `projects_research` | ✅ Enhanced |
| 6 | Scholarly articles | `projects_research` | ✅ Enhanced |
| 7 | Artistic exhibitions | N/A (arts-specific) | - |
| 8 | Leading/critical role | `career` (detailed) | ✅ Existing |
| 9 | High salary | `compensation` | ✅ **NEW BLOCK** |
| 10 | Commercial success (arts) | `projects_research` | ✅ Partial |

#### New Blocks Added
1. **`compensation`** (Block 10) - 7 questions for Criterion 9 (High Salary)
   - Current salary, total compensation
   - Salary comparison, percentile data
   - Special offers, document upload

2. **`final_merits`** (Block 13) - 7 questions for Final Merits Determination
   - Sustained acclaim
   - Recognition scope (national/international)
   - Top percentage in field
   - Unique contributions, industry impact
   - Peer recognition, benefit to US

#### Enhanced Blocks

**Awards (Block 7)** - Added questions:
- `award_level` - National/international level
- `award_criteria` - Selection criteria
- `award_selectivity` - Number of recipients

**Talks/Public Activity (Block 8)** - Added questions:
- Membership requirements and selectivity (Criterion 2)
- Judging venues, frequency, invitation method (Criterion 4)
- Media coverage about applicant, circulation (Criterion 3)

**Projects/Research (Block 6)** - Added questions:
- Journal quality/impact factor (Criterion 6)
- Authorship role (first/corresponding)
- Original contributions, adoption, impact (Criterion 5)
- Patent citations/licensing
- Document upload for citations

**Recommenders (Block 11)** - Added questions:
- Independent vs dependent recommenders
- Recommender credentials and expertise
- International recommenders

#### Summary Statistics
| Metric | Before | After |
|--------|--------|-------|
| Total blocks | 11 | 13 |
| Total questions | ~60 | 90 |
| EB-1A criteria covered | 6/10 | 9/10 |
| Final merits questions | 0 | 7 |

#### Question Tags
All EB-1A related questions now tagged with:
- `eb1a_criterion_1` through `eb1a_criterion_9`
- `eb1a_final_merits`
- `eb1a_evidence`

```python
# Query questions by criterion:
from core.intake.schema import INTAKE_BLOCKS

def get_questions_by_criterion(criterion_num: int):
    tag = f"eb1a_criterion_{criterion_num}"
    for block in INTAKE_BLOCKS:
        for q in block.questions:
            if tag in q.tags:
                yield block.id, q.id, q.text_template
```

---

### 7. AG-UI Protocol Integration (ADDED 2025-12-06)

#### What is AG-UI?
AG-UI (Agent-User Interaction Protocol) is an open, lightweight, event-based protocol
that standardizes how AI agents connect to user-facing applications.
Developed by CopilotKit with LangGraph and CrewAI.

**Key Features:**
- Bi-directional state synchronization
- Real-time streaming via SSE/WebSocket
- Human-in-the-loop support
- Standard event types (~16 events)

#### Architecture

```
┌─────────────────┐     HTTP/SSE/WS      ┌──────────────────┐
│   Frontend UI   │ ◄──────────────────► │   FastAPI + AGUI │
│   (React/Web)   │    AG-UI Events      │     Adapter      │
└─────────────────┘                      └────────┬─────────┘
                                                  │
┌─────────────────┐                      ┌────────▼─────────┐
│  Telegram Bot   │ ◄────────────────────│   MAS Workflow   │
│   (existing)    │   Adapter Events     │   (LangGraph)    │
└─────────────────┘                      └──────────────────┘
```

#### Created Files

| File | Description |
|------|-------------|
| `core/agui/__init__.py` | Module exports |
| `core/agui/events.py` | AG-UI event types + EB-1A custom events |
| `core/agui/adapter.py` | Workflow → AG-UI event adapter |
| `core/agui/middleware.py` | FastAPI router + SSE/WebSocket endpoints |

#### Event Types

**Standard AG-UI Events:**
- `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`
- `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`
- `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`
- `STATE_SNAPSHOT`, `STATE_DELTA`
- `STEP_STARTED`, `STEP_FINISHED`

**EB-1A Custom Events:**
- `AGENT_HANDOFF` - Agent coordination
- `VALIDATION_REQUIRED` - Human-in-the-loop trigger
- `VALIDATION_RESULT` - Human approval/rejection
- `DOCUMENT_GENERATED` - PDF/document ready
- `INTAKE_QUESTION` - Questionnaire question
- `INTAKE_ANSWER` - User answer

#### API Endpoints

```
POST /agui/run          - Execute workflow with SSE streaming
POST /agui/agent        - Invoke single agent with streaming
POST /agui/validation/submit - Submit human validation
GET  /agui/health       - Health check
WS   /agui/ws/{case_id} - WebSocket bi-directional
```

#### Usage Examples

**1. Include router in FastAPI app:**
```python
from core.agui.middleware import include_agui_router

app = FastAPI()
include_agui_router(app)
```

**2. Stream workflow execution:**
```python
from core.agui.adapter import get_agui_adapter

adapter = get_agui_adapter()

async for event in adapter.run_workflow(
    case_id="case-123",
    operation="generate_documents",
    data={"document_type": "petition_letter"},
):
    print(event.to_sse())
```

**3. Frontend SSE consumption (JavaScript):**
```javascript
const eventSource = new EventSource('/agui/run', {
    method: 'POST',
    body: JSON.stringify({
        case_id: 'case-123',
        operation: 'intake_questionnaire'
    })
});

eventSource.addEventListener('TEXT_MESSAGE_CONTENT', (e) => {
    const data = JSON.parse(e.data);
    appendToChat(data.delta);
});

eventSource.addEventListener('VALIDATION_REQUIRED', (e) => {
    const data = JSON.parse(e.data);
    showValidationDialog(data.metadata);
});
```

**4. Human-in-the-loop validation:**
```python
# Backend receives validation approval
await adapter.submit_validation_result(
    validation_id="val-123",
    approved=True,
    feedback="Looks good"
)
```

#### Integration Points

| Component | AG-UI Usage |
|-----------|-------------|
| **Telegram Bot** | Can emit AG-UI events for logging/analytics |
| **Case Site** | Real-time status updates via WebSocket |
| **API** | SSE streaming for document generation |
| **Intake Flow** | `INTAKE_QUESTION`/`INTAKE_ANSWER` events |
| **Validation** | `VALIDATION_REQUIRED` → human approval |

#### Completed Integration (2025-12-06)

1. [x] **AG-UI router integrated into `api/main.py`**
   - Import: `from core.agui.middleware import include_agui_router`
   - Call: `include_agui_router(app)` after other routers

2. [x] **AG-UI events added to intake handlers**
   - `RUN_STARTED` - when intake begins (`intake_start`)
   - `INTAKE_QUESTION` - when question sent (`_send_single_question`)
   - `INTAKE_ANSWER` - when response received (`handle_intake_response`)
   - `RUN_FINISHED` - when intake completes (`_complete_intake`)

3. [x] **React frontend components created**
   - `frontend/components/agui/types.ts` - TypeScript event types
   - `frontend/components/agui/useAGUIStream.ts` - SSE hook
   - `frontend/components/agui/IntakeProgress.tsx` - Progress component
   - `frontend/components/agui/ValidationDialog.tsx` - HITL dialog
   - `frontend/components/agui/README.md` - Documentation

#### Remaining Tasks

4. [ ] Add analytics/logging for AG-UI events
5. [ ] Implement validation approval flow in Telegram

---

### 8. MCP (Model Context Protocol) Integration (ADDED 2025-12-06)

#### What is MCP?
MCP (Model Context Protocol) is Anthropic's protocol for giving LLMs access to external tools and resources. It supports multiple transport types (stdio, HTTP, SSE) and enables dynamic tool discovery.

#### Created Files

| File | Description |
|------|-------------|
| `core/mcp/__init__.py` | Module exports |
| `core/mcp/config.py` | MCPConfig, MCPServerConfig, MCPTransport |
| `core/mcp/client.py` | MCPClientManager, async context manager |
| `core/mcp/tools.py` | Tool filtering, ToolRegistry |

#### Configuration

```python
from core.mcp import MCPConfig, MCPServerConfig, MCPTransport

config = MCPConfig(
    servers=[
        MCPServerConfig(
            name="supabase",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@supabase/mcp-server-supabase"],
            enabled=True,
        ),
        MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            enabled=True,
        ),
    ],
    auto_connect=True,
    retry_on_failure=True,
    max_retries=3,
)
```

#### Usage

```python
from core.mcp import get_mcp_tools, mcp_client_context, MCPClientManager
from core.di import get_container

# Option 1: Via DI container
container = get_container()
mcp_manager = container.get("mcp_manager")
tools = await container.aget("mcp_tools")  # Async tool loading

# Option 2: Context manager
async with mcp_client_context(config) as manager:
    tools = manager.tools
    tool = manager.get_tool_by_name("supabase_query")
    # Use tools...

# Option 3: Global singleton
tools = await get_mcp_tools()
```

#### Transport Types

| Transport | Use Case |
|-----------|----------|
| `STDIO` | Local tools via subprocess (npx, python) |
| `STREAMABLE_HTTP` | Remote HTTP servers |
| `SSE` | Server-Sent Events for streaming |

#### DI Integration

MCP is integrated into the DI container:
- `mcp_manager` - MCPClientManager singleton
- `mcp_tools` - Async factory for loading tools

```python
# In agent code:
container = get_container()
mcp_manager = container.get("mcp_manager")
await mcp_manager.connect()
tools = mcp_manager.tools
```

#### Tool Utilities

```python
from core.mcp import (
    filter_tools_by_names,
    exclude_tools_by_names,
    get_tool_schemas,
    tools_to_openai_functions,
)

# Filter specific tools
db_tools = filter_tools_by_names(tools, ["supabase_query", "supabase_insert"])

# Convert to OpenAI function format
functions = tools_to_openai_functions(tools)
```

#### Dependencies

```bash
pip install langchain-mcp-adapters
```

---

### 9. Frontend Deployment (Next.js + Vercel) - COMPLETED 2025-12-07

#### Production URLs
- **Frontend**: https://eb1a-frontend.vercel.app/
- **Backend API**: https://refreshing-reprieve-production-9802.up.railway.app
- **GitHub (Frontend)**: https://github.com/langgraphsystem/eb1a-frontend
- **GitHub (Backend)**: https://github.com/langgraphsystem/lawercase

#### Tech Stack
- **Framework**: Next.js 14 (App Router)
- **UI Library**: shadcn/ui + Tailwind CSS
- **Protocol**: AG-UI (SSE streaming)
- **Deployment**: Vercel (auto-deploy from main branch)
- **Backend**: Railway (FastAPI)

#### Pages Created
| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Stats overview (cases, documents, intake status) |
| Chat | `/chat` | AI agent chat with AG-UI streaming |
| Cases | `/cases` | Case listing |
| Documents | `/documents` | Document management |

#### Chat Features (v2 - 2025-12-07)
1. **Case Selector Dropdown**
   - Fetches all cases from `/cases` API
   - Shows client name, status, case ID
   - Shows creation/update dates

2. **Persistent Chat History (localStorage)**
   - Each case has its own chat history
   - History saved on each message (excluding streaming)
   - History loaded when switching cases
   - Survives page reload

3. **Clear History Button**
   - Trash icon to clear current case history
   - Resets to welcome message

#### Key Files (web/ folder)
```
web/
├── src/
│   ├── app/
│   │   ├── layout.tsx        # Root layout with navigation
│   │   ├── page.tsx          # Dashboard
│   │   ├── chat/page.tsx     # Chat with AG-UI streaming
│   │   ├── cases/page.tsx    # Cases list
│   │   └── documents/page.tsx
│   ├── components/ui/        # shadcn/ui components
│   └── lib/
│       └── agui.ts           # AG-UI types + API functions
├── .env.local                # NEXT_PUBLIC_API_URL
└── vercel.json               # Vercel config
```

#### Environment Variables
```bash
# web/.env.local
NEXT_PUBLIC_API_URL=https://refreshing-reprieve-production-9802.up.railway.app
```

#### CORS Configuration (Backend)
The backend at `api/main.py` has CORS enabled for Vercel:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://eb1a-frontend.vercel.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Deployment Workflow
1. Make changes in `web/` folder
2. `git add . && git commit -m "feat: ..." && git push`
3. Vercel auto-deploys from `main` branch (~1-2 minutes)

#### AG-UI Integration Details

**Pydantic v2 Fix (events.py)**:
```python
class AGUIEvent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)  # Important for serialization
```

**MegaAgent Response Extraction (adapter.py)**:
```python
# Extract llm_response from MegaAgentResponse for clean chat output
response_text = response.result.get("llm_response", "")
if not response_text:
    # Fallback: summarize retrieved context
    retrieved = response.result.get("retrieved", [])
    ...
```

---

### 10. Intake System Known Issues (2025-12-07)

#### "Block not found" Error
**Symptom**: `/intake_status` shows "❌ Блок не найден"

**Root Cause**: Old cases completed intake before new blocks were added.
- Database has `current_block = "intake_complete"`
- But `"intake_complete"` is not in `BLOCKS_BY_ID`

**Affected Cases**: Those created before 2025-12-05 that completed all 11 original blocks

**New Blocks Added**:
- Block 10: `compensation` (Criterion 9 - High Salary)
- Block 13: `final_merits` (Final Merits Determination)

**Solution**:
```sql
-- For old completed cases, set current_block to first new block
UPDATE mega_agent.case_intake_progress
SET current_block = 'compensation'
WHERE current_block = 'intake_complete';
```

**Prevention**: New cases go through all 13 blocks sequentially

---

### 11. Core Agents & Infrastructure Completion (2025-01-18)

#### ✅ Core Agents Fully Implemented

| Agent | File | Key Features |
|-------|------|--------------|
| **MegaAgent** | `core/groupagents/mega_agent.py` | Central orchestrator, RBAC, command routing, audit logging |
| **SupervisorAgent** | `core/groupagents/supervisor_agent.py` | LLM-driven task planning, agent selection, workflow orchestration |
| **CaseAgent** | `core/groupagents/case_agent.py` | CRUD operations, optimistic locking, search/filtering |
| **WriterAgent** | `core/groupagents/writer_agent.py` | Document generation, LaTeX integration, templates |
| **ValidatorAgent** | `core/groupagents/validator_agent.py` | Rule-based validation, MAGCC assessment, LLM semantic checks |
| **RAGPipelineAgent** | `core/groupagents/rag_pipeline_agent.py` | Hybrid retrieval, context enrichment, caching |
| **EB1Agent** | `core/groupagents/eb1_agent.py` | EB-1A specific workflow orchestration |
| **FeedbackAgent** | `core/groupagents/feedback_agent.py` | User feedback collection and processing |

#### ✅ Infrastructure Complete

| Component | Files | Features |
|-----------|-------|----------|
| **Context Engineering** | `core/context/` | Context manager, compression, relevance scoring, pipelines |
| **Security & RBAC** | `core/security/` | Advanced RBAC, PII detection, prompt injection, audit trail, encryption |
| **Observability** | `core/observability/` | Distributed tracing, metrics, log aggregation, health monitoring |
| **Validation** | `core/validation/` | Confidence scoring, retry handler, quality tracker |
| **Self-Correction** | `core/groupagents/self_correcting_mixin.py` | Auto-retry with validation, confidence scoring |

#### ✅ LLM Models Updated (2025-01-18)

| Provider | New Models |
|----------|-----------|
| **OpenAI** | GPT-5.2, GPT-5.1, GPT-5-mini, GPT-4.1 family, o-series |
| **Anthropic** | Claude 4.5 (Opus, Sonnet, Haiku), Claude 4.1 family |
| **Google** | Gemini 3 Pro/Flash, Gemini 2.5 Pro/Flash |

Old deprecated models removed:
- OpenAI: GPT-4o, GPT-4o-mini
- Anthropic: Claude 3.5 Haiku
- Google: Gemini 2.0 Flash, Gemini 2.0 Flash Lite

#### Module Exports Updated

```python
# Core agents (core/groupagents/__init__.py)
from core.groupagents import (
    MegaAgent,
    SupervisorAgent,
    CaseAgent,
    WriterAgent,
    ValidatorAgent,
    RagPipelineAgent,
    SelfCorrectingMixin,
    # ... models
)

# Security (core/security/__init__.py)
from core.security import (
    RBACManager,
    Permission,
    Role,
    PIIDetector,
    PromptInjectionDetector,
    AuditTrail,
    # ...
)

# Context (core/context/__init__.py)
from core.context import (
    ContextManager,
    ContextCompressor,
    ContextRelevanceScorer,
    # ...
)
```

#### Tests Removed (2025-01-18)
All test files removed from project:
- `tests/` directory (all subdirectories)
- 19 `test_*.py` files from project root
- `pytest.ini`

---

### 12. New AI/ML Features (2025-01-18)

Based on 2025-2026 research on AI agent systems, the following features were added:

#### ✅ A-Mem (Agentic Memory) System
**File**: `core/memory/agentic_memory.py`

Modern memory system based on Zettelkasten principles with:
- Multi-tier memory (Working → Episodic → Semantic → Associative)
- Temporal decay using Ebbinghaus forgetting curve
- Knowledge graph for entity relationships
- Memory consolidation and importance scoring

```python
from core.memory import AgenticMemory, MemoryType

memory = AgenticMemory()

# Add memories
note = await memory.add(
    content="Beneficiary received IEEE Best Paper Award",
    memory_type=MemoryType.EPISODIC,
    tags=["award"],
    case_id="case-123",
)

# Retrieve with temporal decay
memories = await memory.retrieve(
    query="awards",
    memory_types=[MemoryType.EPISODIC],
)

# Knowledge graph
entity = await memory.add_entity(name="IEEE", entity_type="organization")
await memory.add_relation(source_id=person_id, target_id=entity.node_id, relation_type="member_of")
```

#### ✅ Evidence Classifier for EB-1A
**File**: `core/services/evidence_classifier.py`

AI-powered evidence classification inspired by USCIS's ML Evidence Classifier:
- Classifies documents to EB-1A criteria (10 criteria)
- Evidence strength assessment (Strong, Moderate, Weak, Insufficient)
- Case-level evidence assessment with recommendations

```python
from core.services import EvidenceClassifier, EB1ACriterion

classifier = EvidenceClassifier()

result = await classifier.classify_document(
    document_id="doc-123",
    content="NSF letter...",
    filename="nsf_letter.pdf",
)
# result.primary_criterion: EB1ACriterion.ORIGINAL_CONTRIBUTION
# result.strength: EvidenceStrength.STRONG
```

#### ✅ RFE Pattern Analyzer
**File**: `core/services/rfe_analyzer.py`

Analyzes petition for RFE (Request for Evidence) risk patterns:
- Known RFE patterns database with remediation guides
- Success patterns from approved cases
- Risk assessment scoring

```python
from core.services import RFEAnalyzer, RFEIssueType

analyzer = RFEAnalyzer()
assessment = analyzer.analyze_case(case_id, evidence_assessment, documents)
# assessment.risk_level, assessment.issues, assessment.recommendations
```

#### ✅ Document Consistency Checker
**File**: `core/services/document_consistency_checker.py`

Cross-references all petition documents:
- Name consistency across documents
- Date format consistency
- Exhibit reference validation
- Statistical claim verification
- Recommendation letter verification

```python
from core.services import DocumentConsistencyChecker

checker = DocumentConsistencyChecker()
result = await checker.check_case_consistency(
    case_id="case-123",
    petition_letter=petition_text,
    exhibits=[{"id": "A", "content": "..."}],
    beneficiary_info={"name": "John Doe"},
)
# result.is_consistent, result.consistency_score, result.issues
```

#### ✅ LangGraph 1.0 Human-in-the-Loop
**File**: `core/orchestration/human_in_loop.py`

Modern interrupt/Command features from LangGraph 1.0:
- `interrupt()` function for workflow pauses
- `Command` type for routing control
- Interrupt context management
- Approval workflow patterns

```python
from core.orchestration.human_in_loop import (
    HumanInLoopManager,
    create_approval_interrupt,
    interrupt,
    Command,
)

# In workflow node
context = await manager.create_interrupt(
    interrupt_type=InterruptType.APPROVAL_REQUIRED,
    workflow_id=state.thread_id,
    title="Review Petition",
)
response = interrupt(context)

if response.response == "approved":
    return Command(goto="finalize")
```

#### ✅ MCP Tool Search (Dynamic Loading)
**File**: `core/mcp/tool_search.py`

Intelligent tool discovery and dynamic loading:
- Semantic tool search using embeddings
- Context-aware tool recommendations
- Tool usage analytics
- Respects 10% context window threshold

```python
from core.mcp import MCPToolSearch, ToolCategory

search = MCPToolSearch()

# Search for tools
results = await search.search_tools(
    query="read files",
    categories=[ToolCategory.FILE_SYSTEM],
)

# Get recommendations within context budget
recommendation = await search.recommend_tools(
    task="Analyze repository",
    context_limit=8000,
)
```

#### ✅ GraphRAG (Knowledge Graphs)
**File**: `core/rag/graph_rag.py`

Graph-based RAG for enhanced retrieval:
- Multi-hop reasoning through graph traversal
- Entity and relationship management
- Community detection for topic clustering
- Context generation from graph

```python
from core.rag import GraphRAG, NodeType, RelationType, GraphQuery

graph_rag = GraphRAG()

# Add nodes and edges
beneficiary = await graph_rag.add_node(
    node_type=NodeType.BENEFICIARY,
    name="John Doe",
)
award = await graph_rag.add_node(
    node_type=NodeType.AWARD,
    name="IEEE Best Paper",
)
await graph_rag.add_edge(
    source_id=beneficiary.node_id,
    target_id=award.node_id,
    relation_type=RelationType.RECEIVED,
)

# Query graph
results = await graph_rag.search(
    GraphQuery(
        start_query="AI research awards",
        max_hops=2,
    )
)

# Generate context for LLM
context = await graph_rag.generate_context(
    query="What awards?",
    case_id="case-123",
)
```

#### ✅ API Documentation
**File**: `docs/API_REFERENCE.md`

Comprehensive API documentation covering:
- Authentication (JWT, API Keys)
- Core Agents API
- Services API
- Memory System
- RAG Pipeline
- MCP Integration
- Workflows
- Error Handling
- Rate Limits
- Webhooks
- SDKs

---

### Summary of New Files (2025-01-18)

| File | Description |
|------|-------------|
| `core/memory/agentic_memory.py` | A-Mem system with knowledge graphs |
| `core/services/evidence_classifier.py` | EB-1A evidence classification |
| `core/services/rfe_analyzer.py` | RFE risk pattern analysis |
| `core/services/document_consistency_checker.py` | Cross-document consistency |
| `core/orchestration/human_in_loop.py` | LangGraph 1.0 interrupts |
| `core/mcp/tool_search.py` | Dynamic MCP tool loading |
| `core/rag/graph_rag.py` | Graph-based RAG |
| `docs/API_REFERENCE.md` | Comprehensive API docs |
