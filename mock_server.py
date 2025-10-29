"""
Mock FastAPI Server for Document Monitor Testing

This is a fully functional mock backend that simulates the mega_agent_pro
document generation system. Use this for testing the frontend without
a real LangGraph workflow.

Usage:
    python mock_server.py

    Then open http://localhost:8000/monitor/index.html
    The server will simulate progressive document generation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════


class SectionSchema(BaseModel):
    section_id: str
    section_name: str
    section_order: int
    status: str  # pending, in_progress, completed, error
    content_html: str = ""
    updated_at: str
    tokens_used: int | None = None
    error_message: str | None = None


class ExhibitSchema(BaseModel):
    exhibit_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_at: str


class MetadataSchema(BaseModel):
    total_sections: int
    completed_sections: int
    progress_percentage: float
    elapsed_time: int
    estimated_remaining: int
    total_tokens: int
    estimated_cost: float


class LogSchema(BaseModel):
    timestamp: str
    level: str  # info, success, error, warning
    message: str
    agent: str | None = None


class DocumentPreviewResponse(BaseModel):
    thread_id: str
    status: str  # idle, generating, paused, completed, error
    sections: list[SectionSchema]
    exhibits: list[ExhibitSchema]
    metadata: MetadataSchema
    logs: list[LogSchema]


class StartGenerationRequest(BaseModel):
    case_id: str
    document_type: str = "petition"
    user_id: str = "demo-user"


class StartGenerationResponse(BaseModel):
    thread_id: str
    status: str
    message: str


class UploadExhibitResponse(BaseModel):
    success: bool
    exhibit_id: str
    filename: str
    file_path: str


class HumanFeedbackRequest(BaseModel):
    approved: bool
    comments: str | None = None
    suggested_changes: dict[str, Any] | None = None


class HumanFeedbackResponse(BaseModel):
    accepted: bool
    message: str


# ═══════════════════════════════════════════════════════════════════════════
# IN-MEMORY STATE STORAGE
# ═══════════════════════════════════════════════════════════════════════════


class WorkflowStateStore:
    """In-memory storage for workflow states."""

    def __init__(self):
        self.states: dict[str, dict[str, Any]] = {}
        self.pending_approvals: dict[str, dict[str, Any]] = {}

    def create_state(self, thread_id: str, case_id: str, user_id: str) -> None:
        """Create initial workflow state."""
        self.states[thread_id] = {
            "thread_id": thread_id,
            "case_id": case_id,
            "user_id": user_id,
            "status": "generating",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "paused": False,
            "sections": [
                {
                    "section_id": "intro",
                    "section_name": "I. INTRODUCTION",
                    "section_order": 1,
                    "status": "pending",
                    "content_html": "",
                    "updated_at": datetime.now().isoformat(),
                },
                {
                    "section_id": "background",
                    "section_name": "II. BENEFICIARY BACKGROUND",
                    "section_order": 2,
                    "status": "pending",
                    "content_html": "",
                    "updated_at": datetime.now().isoformat(),
                },
                {
                    "section_id": "awards",
                    "section_name": "III. CRITERION 2.1 - AWARDS",
                    "section_order": 3,
                    "status": "pending",
                    "content_html": "",
                    "updated_at": datetime.now().isoformat(),
                },
                {
                    "section_id": "membership",
                    "section_name": "IV. CRITERION 2.2 - MEMBERSHIPS",
                    "section_order": 4,
                    "status": "pending",
                    "content_html": "",
                    "updated_at": datetime.now().isoformat(),
                },
                {
                    "section_id": "publications",
                    "section_name": "V. CRITERION 2.6 - SCHOLARLY ARTICLES",
                    "section_order": 5,
                    "status": "pending",
                    "content_html": "",
                    "updated_at": datetime.now().isoformat(),
                },
            ],
            "exhibits": [],
            "logs": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "info",
                    "message": "Document generation workflow started",
                    "agent": "SupervisorAgent",
                }
            ],
        }

    def get_state(self, thread_id: str) -> dict[str, Any] | None:
        """Get workflow state."""
        return self.states.get(thread_id)

    def update_section(
        self,
        thread_id: str,
        section_id: str,
        status: str,
        content_html: str = "",
        tokens_used: int | None = None,
    ) -> None:
        """Update a section's status and content."""
        state = self.states.get(thread_id)
        if not state:
            return

        for section in state["sections"]:
            if section["section_id"] == section_id:
                section["status"] = status
                section["updated_at"] = datetime.now().isoformat()
                if content_html:
                    section["content_html"] = content_html
                if tokens_used:
                    section["tokens_used"] = tokens_used
                break

    def add_log(self, thread_id: str, level: str, message: str, agent: str | None = None) -> None:
        """Add a log entry."""
        state = self.states.get(thread_id)
        if not state:
            return

        state["logs"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
                "agent": agent,
            }
        )

    def add_exhibit(
        self, thread_id: str, exhibit_id: str, filename: str, file_size: int, mime_type: str
    ) -> None:
        """Add an exhibit."""
        state = self.states.get(thread_id)
        if not state:
            return

        state["exhibits"].append(
            {
                "exhibit_id": exhibit_id,
                "filename": filename,
                "file_path": f"/api/exhibits/{thread_id}/{exhibit_id}_{filename}",
                "file_size": file_size,
                "mime_type": mime_type,
                "uploaded_at": datetime.now().isoformat(),
            }
        )

    def pause(self, thread_id: str) -> None:
        """Pause generation."""
        state = self.states.get(thread_id)
        if state:
            state["paused"] = True
            state["status"] = "paused"

    def resume(self, thread_id: str) -> None:
        """Resume generation."""
        state = self.states.get(thread_id)
        if state:
            state["paused"] = False
            state["status"] = "generating"

    def complete(self, thread_id: str) -> None:
        """Mark as completed."""
        state = self.states.get(thread_id)
        if state:
            state["status"] = "completed"
            state["completed_at"] = datetime.now().isoformat()


# Global state store
state_store = WorkflowStateStore()

# WebSocket connections
websocket_connections: dict[str, list[WebSocket]] = {}

# Background tasks (store references to prevent garbage collection)
background_tasks: set = set()

# ═══════════════════════════════════════════════════════════════════════════
# BACKGROUND TASK: SIMULATE DOCUMENT GENERATION
# ═══════════════════════════════════════════════════════════════════════════


async def simulate_generation(thread_id: str):
    """Simulate progressive document generation."""
    state = state_store.get_state(thread_id)
    if not state:
        return

    # Wait a bit before starting
    await asyncio.sleep(2)

    sections_content = {
        "intro": """
            <h1>PETITION FOR IMMIGRANT CLASSIFICATION<br/>PURSUANT TO INA § 203(b)(1)(A)</h1>
            <h2>I. INTRODUCTION</h2>
            <p class="no-indent">This petition is submitted on behalf of <span class="bold">Dr. Jane Smith</span>,
            a distinguished researcher in artificial intelligence and machine learning, seeking classification as
            an alien of extraordinary ability pursuant to Section 203(b)(1)(A) of the Immigration and Nationality
            Act (INA).</p>
            <p>Dr. Smith has demonstrated sustained national and international acclaim in her field through
            groundbreaking research, prestigious awards, and significant contributions that have advanced the state
            of the art in AI safety and alignment.</p>
            <p>This petition establishes Dr. Smith's eligibility through extensive documentation of her extraordinary
            achievements, including peer-reviewed publications, citations by leading researchers, invited speaking
            engagements at top-tier conferences, and her pivotal role in developing novel approaches to AI interpretability.</p>
        """,
        "background": """
            <h2>II. BENEFICIARY BACKGROUND</h2>
            <p class="no-indent">Dr. Jane Smith earned her Ph.D. in Computer Science from Stanford University in 2018,
            where her dissertation on "Neural Network Interpretability through Mechanistic Analysis" received the
            Outstanding Dissertation Award.</p>
            <p>She currently serves as a Principal Research Scientist at a leading AI research laboratory, where she
            leads a team of 12 researchers focused on AI safety and alignment.</p>
            <h3>Educational Background</h3>
            <ul>
              <li><span class="bold">Ph.D. in Computer Science</span>, Stanford University (2018)</li>
              <li><span class="bold">M.S. in Computer Science</span>, MIT (2014)</li>
              <li><span class="bold">B.S. in Mathematics and Computer Science</span>, UC Berkeley (2012)</li>
            </ul>
        """,
        "awards": """
            <h2>III. CRITERION 2.1 - AWARDS AND PRIZES</h2>
            <p class="no-indent">Dr. Smith has received nationally and internationally recognized awards
            demonstrating her extraordinary ability in artificial intelligence research. These prestigious
            honors were granted based on rigorous peer evaluation and competitive selection processes.</p>

            <h3>NeurIPS Best Paper Award (2023)</h3>
            <p>Awarded by the Neural Information Processing Systems Foundation for the paper
            "Mechanistic Interpretability of Transformer Models." This is the most prestigious award in
            machine learning, with an acceptance rate of 0.1% among 12,000+ submissions.
            See <span class="exhibit">Exhibit 2.1.A</span>.</p>

            <h3>MIT Technology Review 35 Innovators Under 35 (2022)</h3>
            <p>Selected as one of 35 exceptional innovators worldwide under the age of 35.
            Recognition based on transformative contributions to AI safety research.
            See <span class="exhibit">Exhibit 2.1.B</span>.</p>

            <p>These awards clearly establish Dr. Smith's sustained national and international acclaim.</p>
        """,
        "membership": """
            <h2>IV. CRITERION 2.2 - MEMBERSHIPS IN ASSOCIATIONS</h2>
            <p class="no-indent">Dr. Smith holds memberships in prestigious professional associations
            that require outstanding achievements as judged by recognized experts in the field.</p>

            <h3>Association for the Advancement of Artificial Intelligence (AAAI) - Fellow</h3>
            <p>Elected as Fellow in 2023, an honor bestowed upon fewer than 1% of AAAI members.
            Fellows are selected based on significant, sustained contributions to the field of artificial intelligence.
            See <span class="exhibit">Exhibit 2.2.A</span>.</p>

            <h3>IEEE Computer Society - Senior Member</h3>
            <p>Advanced to Senior Member status in 2021, requiring demonstrated professional maturity
            and significant performance in the field. See <span class="exhibit">Exhibit 2.2.B</span>.</p>
        """,
        "publications": """
            <h2>V. CRITERION 2.6 - SCHOLARLY ARTICLES</h2>
            <p class="no-indent">Dr. Smith has authored 42 peer-reviewed publications in leading
            venues, with over 8,500 citations and an h-index of 28, demonstrating the significant
            impact of her research.</p>

            <h3>Selected Publications</h3>
            <p class="no-indent"><span class="bold">1. "Mechanistic Interpretability of Transformer Models"</span></p>
            <p class="indent">Published in: <span class="italic">Neural Information Processing Systems (NeurIPS) 2023</span></p>
            <p class="indent">Citations: 1,245 | Impact: Introduced novel methodology for understanding neural networks</p>
            <p class="indent">See <span class="exhibit">Exhibit 2.6.A</span></p>

            <p class="no-indent"><span class="bold">2. "AI Safety via Debate: Adversarial Collaboration"</span></p>
            <p class="indent">Published in: <span class="italic">Nature Machine Intelligence 2022</span></p>
            <p class="indent">Citations: 892 | Impact: Pioneered new approach to AI alignment</p>
            <p class="indent">See <span class="exhibit">Exhibit 2.6.B</span></p>

            <p>The quality, quantity, and citation impact of these publications establish Dr. Smith's
            extraordinary ability and sustained acclaim in artificial intelligence research.</p>
        """,
    }

    # Generate sections progressively
    for i, section in enumerate(state["sections"]):
        if state["paused"]:
            # Wait while paused
            while state["paused"]:
                await asyncio.sleep(1)

        section_id = section["section_id"]

        # Mark as in_progress
        state_store.update_section(thread_id, section_id, "in_progress")
        state_store.add_log(
            thread_id, "info", f"Generating {section['section_name']}", "WriterAgent"
        )
        await broadcast_update(thread_id)

        # Simulate generation time
        await asyncio.sleep(5)

        # Check if needs approval (for demo: awards section needs approval)
        if section_id == "awards":
            state_store.add_log(
                thread_id, "warning", "Section requires human approval", "SupervisorAgent"
            )
            state_store.pending_approvals[thread_id] = {
                "section_id": section_id,
                "section_name": section["section_name"],
                "content_html": sections_content[section_id],
                "status": "pending_approval",
            }
            await broadcast_update(thread_id)

            # Wait for approval
            while thread_id in state_store.pending_approvals:
                await asyncio.sleep(1)

        # Complete section
        tokens = 300 + (i * 50)
        state_store.update_section(
            thread_id,
            section_id,
            "completed",
            sections_content.get(section_id, "<p>Content generated</p>"),
            tokens,
        )
        state_store.add_log(
            thread_id, "success", f"{section['section_name']} completed", "WriterAgent"
        )
        await broadcast_update(thread_id)

        await asyncio.sleep(2)

    # Mark as completed
    state_store.complete(thread_id)
    state_store.add_log(thread_id, "success", "Document generation completed!", "SupervisorAgent")
    await broadcast_update(thread_id)


async def broadcast_update(thread_id: str):
    """Broadcast state update to all WebSocket connections."""
    if thread_id not in websocket_connections:
        return

    state = state_store.get_state(thread_id)
    if not state:
        return

    response = build_preview_response(thread_id, state)

    # Send to all connected clients
    for ws in websocket_connections[thread_id]:
        try:
            await ws.send_json(response.model_dump())
        except Exception:
            pass  # Connection closed


# ═══════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(title="Mock Document Monitor API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (index.html)
app.mount("/monitor", StaticFiles(directory=".", html=True), name="monitor")


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Mock Document Monitor API",
        "docs": "/docs",
        "monitor": "/monitor/index.html",
    }


@app.post("/api/generate-petition", response_model=StartGenerationResponse)
async def start_generation(request: StartGenerationRequest):
    """Start document generation."""
    thread_id = str(uuid4())

    # Create initial state
    state_store.create_state(thread_id, request.case_id, request.user_id)

    # Start background task for generation
    task = asyncio.create_task(simulate_generation(thread_id))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    return StartGenerationResponse(
        thread_id=thread_id, status="generating", message="Document generation started"
    )


@app.get("/api/document/preview/{thread_id}", response_model=DocumentPreviewResponse)
async def get_preview(thread_id: str):
    """Get document preview (polling endpoint)."""
    state = state_store.get_state(thread_id)

    if not state:
        raise HTTPException(status_code=404, detail="Thread not found")

    return build_preview_response(thread_id, state)


def build_preview_response(thread_id: str, state: dict[str, Any]) -> DocumentPreviewResponse:
    """Build DocumentPreviewResponse from state."""
    sections = [SectionSchema(**s) for s in state["sections"]]
    exhibits = [ExhibitSchema(**e) for e in state["exhibits"]]

    completed = sum(1 for s in state["sections"] if s["status"] == "completed")
    total = len(state["sections"])

    started_at = datetime.fromisoformat(state["started_at"])
    elapsed = int((datetime.now() - started_at).total_seconds())

    if completed > 0:
        avg_time = elapsed / completed
        estimated_remaining = int(avg_time * (total - completed))
    else:
        estimated_remaining = 0

    total_tokens = sum(s.get("tokens_used", 0) for s in state["sections"])
    estimated_cost = (total_tokens / 1000) * 0.02  # $0.02 per 1K tokens

    metadata = MetadataSchema(
        total_sections=total,
        completed_sections=completed,
        progress_percentage=(completed / total * 100) if total > 0 else 0,
        elapsed_time=elapsed,
        estimated_remaining=estimated_remaining,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
    )

    logs = [LogSchema(**log) for log in state["logs"][-50:]]  # Last 50 logs

    # Check for pending approval
    response_status = state["status"]
    if thread_id in state_store.pending_approvals:
        response_status = "pending_approval"

    return DocumentPreviewResponse(
        thread_id=thread_id,
        status=response_status,
        sections=sections,
        exhibits=exhibits,
        metadata=metadata,
        logs=logs,
    )


@app.post("/api/upload-exhibit/{thread_id}", response_model=UploadExhibitResponse)
async def upload_exhibit(thread_id: str, exhibit_id: str = Form(...), file: UploadFile = File(...)):
    """Upload exhibit file."""
    state = state_store.get_state(thread_id)

    if not state:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Read file
    content = await file.read()
    file_size = len(content)

    # Add to state
    state_store.add_exhibit(thread_id, exhibit_id, file.filename, file_size, file.content_type)

    state_store.add_log(
        thread_id, "success", f"Uploaded exhibit {exhibit_id}: {file.filename}", "System"
    )

    await broadcast_update(thread_id)

    return UploadExhibitResponse(
        success=True,
        exhibit_id=exhibit_id,
        filename=file.filename,
        file_path=f"/api/exhibits/{thread_id}/{exhibit_id}_{file.filename}",
    )


@app.get("/api/download-petition-pdf/{thread_id}")
async def download_pdf(thread_id: str):
    """Download PDF (mock)."""
    state = state_store.get_state(thread_id)

    if not state:
        raise HTTPException(status_code=404, detail="Thread not found")

    if state["status"] != "completed":
        raise HTTPException(status_code=400, detail="Document not completed yet")

    # Generate mock PDF content
    pdf_content = b"%PDF-1.4\n%Mock PDF generated by mock_server.py\n"

    return StreamingResponse(
        iter([pdf_content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=petition_{thread_id}.pdf"},
    )


@app.post("/api/pause/{thread_id}")
async def pause_generation(thread_id: str):
    """Pause generation."""
    state = state_store.get_state(thread_id)

    if not state:
        raise HTTPException(status_code=404, detail="Thread not found")

    state_store.pause(thread_id)
    state_store.add_log(thread_id, "info", "Generation paused by user", "System")

    await broadcast_update(thread_id)

    return {"status": "paused", "message": "Generation paused"}


@app.post("/api/resume/{thread_id}")
async def resume_generation(thread_id: str):
    """Resume generation."""
    state = state_store.get_state(thread_id)

    if not state:
        raise HTTPException(status_code=404, detail="Thread not found")

    state_store.resume(thread_id)
    state_store.add_log(thread_id, "info", "Generation resumed by user", "System")

    await broadcast_update(thread_id)

    return {"status": "generating", "message": "Generation resumed"}


@app.get("/api/pending-approval/{thread_id}")
async def get_pending_approval(thread_id: str):
    """Get pending approval details."""
    if thread_id not in state_store.pending_approvals:
        raise HTTPException(status_code=404, detail="No pending approval")

    return state_store.pending_approvals[thread_id]


@app.post("/api/approve/{thread_id}", response_model=HumanFeedbackResponse)
async def approve_section(thread_id: str, feedback: HumanFeedbackRequest):
    """Approve or reject section (Human-in-the-loop)."""
    if thread_id not in state_store.pending_approvals:
        raise HTTPException(status_code=404, detail="No pending approval")

    approval = state_store.pending_approvals[thread_id]
    section_id = approval["section_id"]

    if feedback.approved:
        # Approve: complete the section
        state_store.update_section(
            thread_id, section_id, "completed", approval["content_html"], 450
        )
        state_store.add_log(
            thread_id,
            "success",
            f"Section {approval['section_name']} approved by user",
            "System",
        )
        message = "Section approved and completed"
    else:
        # Reject: mark for regeneration
        state_store.update_section(thread_id, section_id, "pending")
        state_store.add_log(
            thread_id,
            "warning",
            f"Section {approval['section_name']} rejected. Comments: {feedback.comments}",
            "System",
        )
        message = "Section rejected. Will regenerate."

    # Remove from pending
    del state_store.pending_approvals[thread_id]

    await broadcast_update(thread_id)

    return HumanFeedbackResponse(accepted=feedback.approved, message=message)


# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════


@app.websocket("/ws/document/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()

    # Add to connections
    if thread_id not in websocket_connections:
        websocket_connections[thread_id] = []
    websocket_connections[thread_id].append(websocket)

    try:
        # Send initial state
        state = state_store.get_state(thread_id)
        if state:
            response = build_preview_response(thread_id, state)
            await websocket.send_json(response.model_dump())

        # Keep connection alive
        while True:
            # Wait for client messages (ping/pong)
            data = await websocket.receive_text()

            # Echo back (keep-alive)
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        # Remove from connections
        websocket_connections[thread_id].remove(websocket)
        if not websocket_connections[thread_id]:
            del websocket_connections[thread_id]


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("🚀 Starting Mock Document Monitor API Server")
    print("=" * 80)
    print()
    print("📍 API Documentation:  http://localhost:8000/docs")
    print("🎯 Monitor Interface:  http://localhost:8000/monitor/index.html")
    print()
    print("Features:")
    print("  ✅ Progressive document generation (5 sections)")
    print("  ✅ Human-in-the-loop approval (awards section)")
    print("  ✅ WebSocket real-time updates")
    print("  ✅ File upload simulation")
    print("  ✅ Pause/Resume functionality")
    print("  ✅ PDF download (mock)")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
