# 🏗️ Document Monitor - Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEGA AGENT PRO - DOCUMENT MONITOR                   │
│                         Real-time Legal Document Generation                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (index.html)                                                      │
│  Single-page application (Vanilla JS, Zero Dependencies)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────────┐  ┌─────────────────┐              │
│  │   SIDEBAR    │  │   MAIN CONTENT   │  │  CONTROLS PANEL │              │
│  │              │  │                  │  │                 │              │
│  │ • Sections   │  │ • Document       │  │ • Start/Pause   │              │
│  │   - Intro    │  │   Preview        │  │ • Upload File   │              │
│  │   - Awards   │  │   (Times New     │  │ • Download PDF  │              │
│  │   - Pubs     │  │    Roman 11pt)   │  │ • Statistics    │              │
│  │              │  │                  │  │ • Logs          │              │
│  │ • Exhibits   │  │ • Real-time      │  │                 │              │
│  │   - 2.1.A    │  │   Updates        │  │ Progress: 67%   │              │
│  │   - 2.6.B    │  │                  │  │ Time: 02:34     │              │
│  └──────────────┘  └──────────────────┘  └─────────────────┘              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DocumentMonitor Class                                              │   │
│  │  • startPolling() - Begin monitoring                                │   │
│  │  • poll() - Fetch status every 2s                                   │   │
│  │  • updateUI() - Refresh all panels                                  │   │
│  │  • stopPolling() - Clean shutdown                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP Polling (every 2s)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  API LAYER (FastAPI)                                                        │
│  api/routes/document_monitor.py                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  POST /api/generate-petition                                                │
│  ├─ Create thread_id                                                        │
│  ├─ Initialize WorkflowState                                                │
│  ├─ Start LangGraph workflow                                                │
│  └─ Return thread_id                                                        │
│                                                                             │
│  GET /api/document/preview/{thread_id}  ← POLLED ENDPOINT                  │
│  ├─ Load WorkflowState from storage                                         │
│  ├─ Convert to DocumentPreviewResponse                                      │
│  └─ Return JSON (sections, exhibits, metadata, logs)                        │
│                                                                             │
│  POST /api/upload-exhibit/{thread_id}                                       │
│  ├─ Save file to storage                                                    │
│  ├─ Update WorkflowState                                                    │
│  └─ Return file metadata                                                    │
│                                                                             │
│  GET /api/download-petition-pdf/{thread_id}                                 │
│  ├─ Generate PDF from HTML                                                  │
│  └─ Return binary PDF                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  WORKFLOW ORCHESTRATION (LangGraph)                                         │
│  core/orchestration/workflow_graph.py                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  StateGraph: EB-1A Petition Generation                              │   │
│  │                                                                      │   │
│  │  START → CaseAgent → WriterAgent → ValidatorAgent → END             │   │
│  │           │           │ (loop)     │                                │   │
│  │           │           │            │                                │   │
│  │           └─ Retrieve case data    └─ Self-correction loop          │   │
│  │           └─ Load exhibits                                          │   │
│  │                       │                                             │   │
│  │                       ├─ Section 1: Introduction                    │   │
│  │                       ├─ Section 2: Background                      │   │
│  │                       ├─ Section 3: Awards (2.1)                    │   │
│  │                       ├─ Section 4: Memberships (2.2)               │   │
│  │                       └─ Section 5: Publications (2.6)              │   │
│  │                                                                      │   │
│  │  After each node: Update WorkflowState → Save to storage            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT LAYER                                                                │
│  core/groupagents/                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐              │
│  │  CaseAgent     │  │  WriterAgent   │  │  ValidatorAgent │              │
│  │                │  │                │  │                 │              │
│  │ • Load case    │  │ • Generate     │  │ • Validate      │              │
│  │   data         │  │   sections     │  │   content       │              │
│  │ • Retrieve     │  │ • Apply        │  │ • Check         │              │
│  │   exhibits     │  │   templates    │  │   criteria      │              │
│  │ • Manage       │  │ • Format HTML  │  │ • Suggest       │              │
│  │   documents    │  │                │  │   improvements  │              │
│  └────────────────┘  └────────────────┘  └─────────────────┘              │
│          │                    │                     │                       │
│          └────────────────────┼─────────────────────┘                       │
│                               │                                             │
│                               ▼                                             │
│                    ┌──────────────────────┐                                 │
│                    │  SupervisorAgent     │                                 │
│                    │  • Orchestrate       │                                 │
│                    │  • Route tasks       │                                 │
│                    │  • Monitor progress  │                                 │
│                    └──────────────────────┘                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STORAGE & MEMORY                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐  ┌────────────────┐  ┌─────────────────────┐        │
│  │  WorkflowState    │  │  MemoryManager │  │  File Storage       │        │
│  │  Storage          │  │                │  │                     │        │
│  │                   │  │ • Episodic     │  │ • Exhibits          │        │
│  │ • Redis           │  │ • Semantic     │  │ • Generated PDFs    │        │
│  │   OR              │  │ • Working      │  │                     │        │
│  │ • PostgreSQL      │  │                │  │ • Local FS          │        │
│  │   OR              │  │ • RAG pipeline │  │   OR                │        │
│  │ • LangGraph       │  │                │  │ • S3 / Azure Blob   │        │
│  │   Checkpointer    │  │                │  │                     │        │
│  └───────────────────┘  └────────────────┘  └─────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Document Generation

```
User Action                Frontend                  Backend                 Workflow
─────────────────────────────────────────────────────────────────────────────────

1. Click "Start"
    │
    ├──► POST /generate-petition
    │                              │
    │                              ├──► Create thread_id
    │                              │    Initialize state
    │                              │
    │                              ├──► Start LangGraph
    │                              │         │
    │◄─── Return thread_id ────────┘         │
    │                                         │
    │                                         ├──► CaseAgent: Load case
    │                                         │         │
2. Start polling (every 2s)                   │         ├─ Retrieve docs
    │                                         │         └─ Load exhibits
    ├──► GET /preview/{id}                    │
    │                              │           │
    │                              ├──► Load state from storage
    │                              │           │
    │◄─── Return status ───────────┤           │
    │     • sections: []                       │
    │     • status: "generating"               │
    │     • progress: 0%                       ├──► WriterAgent: Section 1
    │                                         │         │
3. Poll again                                  │         ├─ Generate intro
    │                                         │         ├─ Format HTML
    ├──► GET /preview/{id}                    │         └─ Save to state
    │                              │           │
    │                              ├──► Load updated state
    │                              │           │
    │◄─── Return status ───────────┤           │
    │     • sections: [{                       │
    │         id: "intro",                     │
    │         status: "completed",             │
    │         content_html: "<h1>..."          │
    │       }]                                 │
    │     • progress: 20%                      ├──► WriterAgent: Section 2
    │                                         │         │
    ├──► Update UI                             │         └─ Generate background
    │     • Render section in main area       │
    │     • Update sidebar status             ├──► ValidatorAgent
    │     • Update progress bar               │         │
    │                                         │         ├─ Validate section 1
4. Continue polling...                         │         ├─ Check criteria
    │                                         │         └─ Return feedback
    │                                         │
5. Upload exhibit                              │
    │                                         │
    ├──► POST /upload-exhibit                  │
    │     FormData:                            │
    │     • exhibit_id: "2.1.A"               │
    │     • file: [binary]                    │
    │                              │           │
    │                              ├──► Save file
    │                              │    Update state
    │                              │           │
    │◄─── Return success ──────────┘           │
    │                                         │
6. Generation completes                        │
    │                                         │
    ├──► GET /preview/{id}                    │
    │                              │           │
    │◄─── Return status ───────────┤           │
    │     • status: "completed"               ▼
    │     • progress: 100%               Workflow END
    │
    ├──► Stop polling
    │
    ├──► Enable "Download PDF" button
    │
7. Download PDF
    │
    ├──► GET /download-pdf/{id}
    │                              │
    │                              ├──► Generate PDF
    │                              │    (weasyprint/pdfkit)
    │                              │
    │◄─── Return PDF binary ───────┘
    │
    └──► Browser downloads file
```

---

## State Management

### WorkflowState Structure (Extended for Monitor)

```python
class WorkflowState(BaseModel):
    # Core fields (existing)
    thread_id: str
    user_id: str | None
    case_id: str | None
    workflow_step: str  # "generating" | "completed" | "error"

    # Document workflow data (EXTENDED)
    document_data: dict[str, Any] = {
        "sections": [
            {
                "id": "intro",
                "name": "I. INTRODUCTION",
                "order": 1,
                "status": "pending",      # pending → in_progress → completed
                "content_html": "",       # Generated HTML with styles
                "updated_at": "2025-01-...",
                "tokens_used": 0,
                "error_message": None
            },
            # ... more sections
        ],

        "exhibits": [
            {
                "exhibit_id": "2.1.A",
                "filename": "award.pdf",
                "file_path": "/uploads/...",
                "file_size": 123456,
                "mime_type": "application/pdf",
                "uploaded_at": "2025-01-..."
            },
            # ... more exhibits
        ],

        "logs": [
            {
                "timestamp": "2025-01-...",
                "level": "info",
                "message": "Starting generation",
                "agent": "SupervisorAgent"
            },
            # ... more logs
        ],

        "started_at": "2025-01-...",
        "completed_at": None
    }

    # Error handling
    error: str | None
```

### State Updates in Workflow Nodes

```python
async def writer_agent_node(state: WorkflowState) -> WorkflowState:
    """Generate a document section."""

    section_id = state.current_section  # e.g., "intro"

    # 1. Mark as in_progress
    update_section_status(state, section_id, "in_progress")
    await save_state(state)

    # 2. Generate content
    try:
        content = await writer_agent.generate(...)

        # 3. Mark as completed
        update_section(state, section_id, {
            "status": "completed",
            "content_html": content.html,
            "tokens_used": content.tokens,
            "updated_at": datetime.now().isoformat()
        })

        # 4. Log success
        add_log(state, "success", f"Section {section_id} completed", "WriterAgent")

    except Exception as e:
        # 5. Mark as error
        update_section(state, section_id, {
            "status": "error",
            "error_message": str(e)
        })

        add_log(state, "error", f"Failed to generate {section_id}", "WriterAgent")

    # 6. Save updated state
    await save_state(state)

    return state
```

---

## Performance Optimization

### 1. Polling Optimization

```javascript
// Adaptive polling interval
class DocumentMonitor {
  constructor(threadId) {
    this.pollInterval = 2000;  // Initial: 2s
  }

  async poll() {
    const data = await this.fetchStatus();

    // Slow down polling if nothing changed
    if (this.noChangesCount > 5) {
      this.pollInterval = 5000;  // Increase to 5s
    }

    // Speed up during active generation
    if (data.status === 'generating') {
      this.pollInterval = 2000;  // Keep at 2s
    }
  }
}
```

### 2. Backend Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache completed sections (they don't change)
@lru_cache(maxsize=1000)
def get_completed_section(section_id: str, version: int) -> str:
    """Cache generated HTML for completed sections."""
    return load_section_html(section_id, version)

# Cache state for 1 second (reduce DB queries)
state_cache = {}

async def load_workflow_state(thread_id: str) -> WorkflowState:
    if thread_id in state_cache:
        cached_state, cached_at = state_cache[thread_id]
        if datetime.now() - cached_at < timedelta(seconds=1):
            return cached_state

    state = await db.load_state(thread_id)
    state_cache[thread_id] = (state, datetime.now())
    return state
```

### 3. Frontend Rendering Optimization

```javascript
// Only re-render changed sections
updateMainContent(newSections) {
  newSections.forEach(section => {
    const element = document.getElementById(`section-${section.id}`);

    // Skip if content unchanged
    if (element && element.dataset.version === section.version) {
      return;
    }

    // Update only if changed
    element.innerHTML = section.content_html;
    element.dataset.version = section.version;
  });
}

// Virtual scrolling for long documents
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      renderSectionContent(entry.target);
    }
  });
});
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SECURITY LAYERS                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. AUTHENTICATION                                                          │
│     ┌─────────────────────────────────────────────────────────────┐        │
│     │  • JWT token in Authorization header                         │        │
│     │  • API key for machine-to-machine                            │        │
│     │  • Session management                                         │        │
│     └─────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  2. AUTHORIZATION                                                           │
│     ┌─────────────────────────────────────────────────────────────┐        │
│     │  • RBAC (Role-Based Access Control)                          │        │
│     │  • User can only access own threads                          │        │
│     │  • Admin can view all threads                                │        │
│     └─────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  3. INPUT VALIDATION                                                        │
│     ┌─────────────────────────────────────────────────────────────┐        │
│     │  • Pydantic schemas for all requests                         │        │
│     │  • File type validation (MIME check)                         │        │
│     │  • File size limits (max 10MB)                               │        │
│     │  • Exhibit ID format validation (regex)                      │        │
│     └─────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  4. OUTPUT SANITIZATION                                                     │
│     ┌─────────────────────────────────────────────────────────────┐        │
│     │  • HTML sanitization with bleach                             │        │
│     │  • Only allowed tags: h1-h3, p, span, div, ul, ol, li, a     │        │
│     │  • Only allowed attributes: class, href                      │        │
│     │  • Strip all scripts and event handlers                      │        │
│     └─────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  5. RATE LIMITING                                                           │
│     ┌─────────────────────────────────────────────────────────────┐        │
│     │  • 30 requests/minute per IP (polling endpoint)              │        │
│     │  • 5 uploads/minute per user                                 │        │
│     │  • 10 generations/hour per user                              │        │
│     └─────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  6. SECURE FILE STORAGE                                                     │
│     ┌─────────────────────────────────────────────────────────────┐        │
│     │  • Files stored outside web root                             │        │
│     │  • Randomized filenames (UUID)                               │        │
│     │  • Virus scanning before storage                             │        │
│     │  • Signed URLs for downloads (time-limited)                  │        │
│     └─────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  7. ENCRYPTION                                                              │
│     ┌─────────────────────────────────────────────────────────────┐        │
│     │  • HTTPS only (TLS 1.3)                                      │        │
│     │  • Encrypted at rest (database encryption)                   │        │
│     │  • Secure cookies (httpOnly, secure, sameSite)               │        │
│     └─────────────────────────────────────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Production Setup (Kubernetes)

```yaml
# k8s deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: document-monitor
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: frontend
        image: nginx:alpine
        volumeMounts:
        - name: static-files
          mountPath: /usr/share/nginx/html
          # Contains: index.html

      - name: backend
        image: mega-agent-pro:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          value: redis://redis-service:6379

      volumes:
      - name: static-files
        configMap:
          name: monitor-static
```

### Load Balancing

```
                  ┌─────────────┐
                  │   Nginx     │
                  │  (Ingress)  │
                  └──────┬──────┘
                         │
           ──────────────┼──────────────
          │              │              │
    ┌─────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
    │ Backend 1 │  │Backend 2 │  │Backend 3 │
    │ (FastAPI) │  │(FastAPI) │  │(FastAPI) │
    └─────┬─────┘  └────┬─────┘  └────┬─────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                   ┌─────▼─────┐
                   │   Redis   │
                   │  (State)  │
                   └───────────┘
```

---

## Monitoring & Observability

```
Application Metrics                  System Metrics
─────────────────────────────────────────────────────────

• document_generations_total         • CPU usage
• generation_duration_seconds        • Memory usage
• section_generation_duration        • Disk I/O
• polling_requests_total             • Network traffic
• upload_success_rate
• pdf_download_total
• error_rate_by_type

Logging                              Tracing
─────────────────────────────────────────────────────────

• Structured logs (JSON)             • OpenTelemetry
• Log levels: DEBUG, INFO, ERROR     • Distributed tracing
• Request ID tracking                • Span visualization
• User action audit trail            • Performance profiling

Alerting                             Dashboards
─────────────────────────────────────────────────────────

• Error rate > 5%                    • Grafana
• Generation time > 5 min            • Prometheus
• Polling failures > 10              • Real-time metrics
• Storage usage > 80%                • Custom alerts
```

---

**Documentation created**: 2025-01-XX
**Version**: 1.0.0
**Author**: Claude Code for mega_agent_pro
