"""
FastAPI routes for Document Generation Monitor.

Provides real-time status updates for document generation workflows,
supporting the frontend monitoring dashboard (index.html).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import structlog

from core.storage.document_workflow_store import get_document_workflow_store
from core.websocket_manager import manager as ws_manager

# Optional: Import for authentication
# from api.deps import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["document-monitor"])

# Get workflow store instance
workflow_store = get_document_workflow_store()

# Store background tasks to prevent garbage collection
background_tasks: set[asyncio.Task] = set()


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════


class SectionSchema(BaseModel):
    """Individual document section."""

    section_id: str = Field(..., description="Unique section identifier")
    section_name: str = Field(..., description="Display name (e.g., 'I. INTRODUCTION')")
    section_order: int = Field(..., description="Order in document (1, 2, 3...)")
    status: Literal["pending", "in_progress", "completed", "error"] = Field(
        ..., description="Current generation status"
    )
    content_html: str = Field("", description="HTML content with inline styles")
    updated_at: datetime = Field(default_factory=datetime.now)
    tokens_used: int | None = Field(None, description="Tokens used for this section")
    error_message: str | None = Field(None, description="Error details if status=error")


class ExhibitSchema(BaseModel):
    """Uploaded exhibit file."""

    exhibit_id: str = Field(..., description="Exhibit ID (e.g., '2.1.A')")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="URL/path for download")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    uploaded_at: datetime = Field(default_factory=datetime.now)


class MetadataSchema(BaseModel):
    """Workflow metadata and statistics."""

    total_sections: int
    completed_sections: int
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    elapsed_time: int = Field(..., description="Elapsed time in seconds")
    estimated_remaining: int = Field(..., description="Estimated remaining time in seconds")
    total_tokens: int
    estimated_cost: float = Field(..., description="Estimated cost in USD")


class LogSchema(BaseModel):
    """Log entry."""

    timestamp: datetime = Field(default_factory=datetime.now)
    level: Literal["info", "success", "error", "warning"]
    message: str
    agent: str | None = Field(None, description="Agent that generated the log")


class DocumentPreviewResponse(BaseModel):
    """Complete document generation status response."""

    thread_id: str
    status: Literal["idle", "generating", "paused", "completed", "error"]
    sections: list[SectionSchema]
    exhibits: list[ExhibitSchema]
    metadata: MetadataSchema
    logs: list[LogSchema]


class StartGenerationRequest(BaseModel):
    """Request to start document generation."""

    case_id: str = Field(..., description="Case ID")
    document_type: Literal["petition", "letter", "memo"] = Field(
        "petition", description="Type of document to generate"
    )
    user_id: str = Field(..., description="User ID")


class StartGenerationResponse(BaseModel):
    """Response after starting generation."""

    thread_id: str
    status: str
    message: str


class UploadExhibitResponse(BaseModel):
    """Response after uploading an exhibit."""

    success: bool
    exhibit_id: str
    filename: str
    file_path: str


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/generate-petition", response_model=StartGenerationResponse)
async def start_document_generation(
    request: StartGenerationRequest,
    # user = Depends(get_current_user),  # Uncomment for auth
) -> StartGenerationResponse:
    """
    Start a new document generation workflow.

    Creates a new LangGraph workflow thread and initiates the document
    generation process.

    Args:
        request: Generation parameters (case_id, document_type, user_id)

    Returns:
        StartGenerationResponse with thread_id for polling

    Raises:
        HTTPException: If case not found or workflow fails to start
    """

    try:
        thread_id = str(uuid4())

        # Get section definitions for document type
        sections = get_section_definitions(request.document_type)

        # Create initial workflow state
        initial_state = {
            "thread_id": thread_id,
            "user_id": request.user_id,
            "case_id": request.case_id,
            "document_type": request.document_type,
            "status": "generating",
            "sections": sections,
            "exhibits": [],
            "logs": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "info",
                    "message": f"Starting {request.document_type} generation for case {request.case_id}",
                    "agent": "DocumentMonitor",
                }
            ],
            "started_at": datetime.now().isoformat(),
            "error_message": None,
        }

        # Save initial state
        await workflow_store.save_state(thread_id, initial_state)

        # Start background document generation workflow
        task = asyncio.create_task(_run_document_generation_workflow(thread_id, request))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

        logger.info(
            "document_generation_started",
            thread_id=thread_id,
            case_id=request.case_id,
            document_type=request.document_type,
            user_id=request.user_id,
        )

        return StartGenerationResponse(
            thread_id=thread_id,
            status="generating",
            message=f"Document generation started for case {request.case_id}",
        )

    except Exception as e:
        logger.error("start_generation_error", error=str(e), request=request.model_dump())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start document generation: {e!s}",
        )


@router.get("/document/preview/{thread_id}", response_model=DocumentPreviewResponse)
async def get_document_preview(
    thread_id: str,
    # user = Depends(get_current_user),  # Uncomment for auth
) -> DocumentPreviewResponse:
    """
    Get current status of document generation.

    This endpoint is polled by the frontend every 2 seconds to get updates.
    Should be fast and efficient.

    Args:
        thread_id: Workflow thread ID from start_document_generation

    Returns:
        DocumentPreviewResponse with current state

    Raises:
        HTTPException: If thread_id not found
    """

    try:
        # Load workflow state
        state = await workflow_store.load_state(thread_id)

        if not state:
            raise HTTPException(status_code=404, detail=f"Workflow thread {thread_id} not found")

        # Convert sections to schema
        sections = []
        for sec_data in state.get("sections", []):
            sections.append(
                SectionSchema(
                    section_id=sec_data.get("id", sec_data.get("section_id", "")),
                    section_name=sec_data.get("name", sec_data.get("section_name", "")),
                    section_order=sec_data.get("order", sec_data.get("section_order", 0)),
                    status=sec_data.get("status", "pending"),
                    content_html=sec_data.get("content_html", ""),
                    updated_at=datetime.fromisoformat(
                        sec_data.get("updated_at", datetime.now().isoformat())
                    ),
                    tokens_used=sec_data.get("tokens_used"),
                    error_message=sec_data.get("error_message"),
                )
            )

        # Convert exhibits to schema
        exhibits = []
        for ex_data in state.get("exhibits", []):
            exhibits.append(
                ExhibitSchema(
                    exhibit_id=ex_data["exhibit_id"],
                    filename=ex_data["filename"],
                    file_path=ex_data["file_path"],
                    file_size=ex_data["file_size"],
                    mime_type=ex_data["mime_type"],
                    uploaded_at=datetime.fromisoformat(ex_data["uploaded_at"]),
                )
            )

        # Calculate metadata
        metadata = calculate_metadata(state)

        # Get last 50 logs
        all_logs = state.get("logs", [])
        recent_logs = all_logs[-50:] if len(all_logs) > 50 else all_logs

        logs = []
        for log_data in recent_logs:
            logs.append(
                LogSchema(
                    timestamp=datetime.fromisoformat(log_data["timestamp"]),
                    level=log_data["level"],
                    message=log_data["message"],
                    agent=log_data.get("agent"),
                )
            )

        return DocumentPreviewResponse(
            thread_id=thread_id,
            status=state.get("status", "idle"),
            sections=sections,
            exhibits=exhibits,
            metadata=metadata,
            logs=logs,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_preview_error", thread_id=thread_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document preview: {e!s}",
        )


@router.post("/upload-exhibit/{thread_id}", response_model=UploadExhibitResponse)
async def upload_exhibit(
    thread_id: str,
    exhibit_id: str = Form(...),
    file: UploadFile = File(...),
    # user = Depends(get_current_user),  # Uncomment for auth
) -> UploadExhibitResponse:
    """
    Upload an exhibit file for the document.

    Args:
        thread_id: Workflow thread ID
        exhibit_id: Exhibit identifier (e.g., "2.1.A")
        file: Uploaded file

    Returns:
        UploadExhibitResponse with file details

    Raises:
        HTTPException: If upload fails or thread not found
    """

    try:
        # Validate thread exists
        state = await workflow_store.load_state(thread_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Workflow thread {thread_id} not found")

        # Create upload directory
        upload_dir = Path("uploads") / thread_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file with exhibit_id prefix
        safe_filename = f"{exhibit_id}_{file.filename}".replace(" ", "_")
        file_path = upload_dir / safe_filename

        # Read and save file content
        content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Prepare exhibit metadata
        exhibit_data = {
            "exhibit_id": exhibit_id,
            "filename": file.filename,
            "file_path": f"/api/exhibits/{thread_id}/{safe_filename}",
            "file_size": len(content),
            "mime_type": file.content_type or "application/octet-stream",
            "uploaded_at": datetime.now().isoformat(),
        }

        # Add exhibit to state
        await workflow_store.add_exhibit(thread_id, exhibit_data)

        # Log upload event
        await workflow_store.add_log(
            thread_id,
            {
                "timestamp": datetime.now().isoformat(),
                "level": "success",
                "message": f"Uploaded exhibit {exhibit_id}: {file.filename} ({len(content)} bytes)",
                "agent": "System",
            },
        )

        logger.info(
            "exhibit_uploaded",
            thread_id=thread_id,
            exhibit_id=exhibit_id,
            filename=file.filename,
            file_size=len(content),
        )

        return UploadExhibitResponse(
            success=True,
            exhibit_id=exhibit_id,
            filename=file.filename,
            file_path=exhibit_data["file_path"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "upload_exhibit_error", thread_id=thread_id, exhibit_id=exhibit_id, error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload exhibit: {e!s}",
        )


@router.get("/download-petition-pdf/{thread_id}")
async def download_petition_pdf(
    thread_id: str,
    # user = Depends(get_current_user),  # Uncomment for auth
):
    """
    Download the generated petition as PDF.

    Args:
        thread_id: Workflow thread ID

    Returns:
        PDF file as binary response

    Raises:
        HTTPException: If document not completed or PDF generation fails
    """

    try:
        # Load workflow state
        state = await workflow_store.load_state(thread_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Workflow thread {thread_id} not found")

        # Check if generation is completed
        if state.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Document generation not completed yet. Current status: {state.get('status')}",
            )

        # Check if PDF exists or generate it
        pdf_dir = Path("pdfs")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f"{thread_id}.pdf"

        if not pdf_path.exists():
            # Generate PDF from sections
            pdf_path = await generate_pdf(state, thread_id)

        if not pdf_path.exists():
            raise HTTPException(status_code=500, detail="PDF generation failed")

        logger.info("pdf_download", thread_id=thread_id, pdf_path=str(pdf_path))

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"petition_{thread_id}.pdf",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("download_pdf_error", thread_id=thread_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download PDF: {e!s}",
        )


@router.post("/pause/{thread_id}")
async def pause_generation(
    thread_id: str,
    # user = Depends(get_current_user),  # Uncomment for auth
):
    """
    Pause document generation.

    Args:
        thread_id: Workflow thread ID

    Returns:
        Status message

    Raises:
        HTTPException: If thread not found or cannot be paused
    """

    try:
        # Load state
        state = await workflow_store.load_state(thread_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Workflow thread {thread_id} not found")

        current_status = state.get("status")

        # Check if can be paused
        if current_status not in ["generating", "in_progress"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause workflow in status '{current_status}'. Must be 'generating' or 'in_progress'.",
            )

        # Update status to paused
        success = await workflow_store.update_workflow_status(thread_id, "paused")

        if not success:
            raise HTTPException(status_code=500, detail="Failed to pause workflow")

        # Log pause event
        await workflow_store.add_log(
            thread_id,
            {
                "timestamp": datetime.now().isoformat(),
                "level": "warning",
                "message": "Document generation paused by user",
                "agent": "System",
            },
        )

        logger.info("workflow_paused", thread_id=thread_id)

        return {"status": "paused", "message": "Document generation paused successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("pause_error", thread_id=thread_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pause generation: {e!s}",
        )


@router.post("/resume/{thread_id}")
async def resume_generation(
    thread_id: str,
    # user = Depends(get_current_user),  # Uncomment for auth
):
    """
    Resume paused document generation.

    Args:
        thread_id: Workflow thread ID

    Returns:
        Status message

    Raises:
        HTTPException: If thread not found or cannot be resumed
    """

    try:
        # Load state
        state = await workflow_store.load_state(thread_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Workflow thread {thread_id} not found")

        current_status = state.get("status")

        # Check if can be resumed
        if current_status != "paused":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume workflow in status '{current_status}'. Must be 'paused'.",
            )

        # Update status to generating
        success = await workflow_store.update_workflow_status(thread_id, "generating")

        if not success:
            raise HTTPException(status_code=500, detail="Failed to resume workflow")

        # Log resume event
        await workflow_store.add_log(
            thread_id,
            {
                "timestamp": datetime.now().isoformat(),
                "level": "info",
                "message": "Document generation resumed",
                "agent": "System",
            },
        )

        # Restart background workflow
        request_data = StartGenerationRequest(
            case_id=state.get("case_id", ""),
            document_type=state.get("document_type", "petition"),
            user_id=state.get("user_id", ""),
        )
        task = asyncio.create_task(
            _run_document_generation_workflow(thread_id, request_data, resume=True)
        )
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

        logger.info("workflow_resumed", thread_id=thread_id)

        return {"status": "generating", "message": "Document generation resumed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("resume_error", thread_id=thread_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume generation: {e!s}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def calculate_metadata(state: dict[str, Any]) -> MetadataSchema:
    """
    Calculate metadata from workflow state.

    Args:
        state: Workflow state dictionary

    Returns:
        MetadataSchema with calculated statistics
    """

    sections = state.get("sections", [])
    completed = sum(1 for s in sections if s.get("status") == "completed")
    total = len(sections)

    # Calculate elapsed time
    started_at = datetime.fromisoformat(state.get("started_at", datetime.now().isoformat()))
    elapsed = int((datetime.now() - started_at).total_seconds())

    # Estimate remaining time (simple linear projection)
    if completed > 0:
        avg_time_per_section = elapsed / completed
        remaining_sections = total - completed
        estimated_remaining = int(avg_time_per_section * remaining_sections)
    else:
        estimated_remaining = 0

    # Calculate tokens
    total_tokens = sum(s.get("tokens_used", 0) for s in sections)

    # Estimate cost (example: $0.01 per 1000 tokens)
    estimated_cost = (total_tokens / 1000) * 0.01

    return MetadataSchema(
        total_sections=total,
        completed_sections=completed,
        progress_percentage=(completed / total * 100) if total > 0 else 0,
        elapsed_time=elapsed,
        estimated_remaining=estimated_remaining,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
    )


def get_section_definitions(document_type: str) -> list[dict[str, Any]]:
    """
    Get section definitions for a document type.

    Args:
        document_type: Type of document ("petition", "letter", "memo")

    Returns:
        List of section definitions
    """

    if document_type == "petition":
        return [
            {"id": "intro", "name": "I. INTRODUCTION", "order": 1, "status": "pending"},
            {
                "id": "background",
                "name": "II. BENEFICIARY BACKGROUND",
                "order": 2,
                "status": "pending",
            },
            {
                "id": "awards",
                "name": "III. CRITERION 2.1 - AWARDS",
                "order": 3,
                "status": "pending",
            },
            {
                "id": "membership",
                "name": "IV. CRITERION 2.2 - MEMBERSHIPS",
                "order": 4,
                "status": "pending",
            },
            {
                "id": "publications",
                "name": "V. CRITERION 2.6 - SCHOLARLY ARTICLES",
                "order": 5,
                "status": "pending",
            },
            # Add more sections as needed
        ]
    if document_type == "letter":
        return [
            {"id": "header", "name": "Header", "order": 1, "status": "pending"},
            {"id": "body", "name": "Body", "order": 2, "status": "pending"},
            {"id": "closing", "name": "Closing", "order": 3, "status": "pending"},
        ]
    return [
        {"id": "memo", "name": "Memorandum", "order": 1, "status": "pending"},
    ]


async def _run_document_generation_workflow(
    thread_id: str,
    request: StartGenerationRequest,
    resume: bool = False,
) -> None:
    """
    Background task to run real LangGraph document generation workflow.

    Integrates with WriterAgent, ValidatorAgent, and MemoryManager.
    Broadcasts WebSocket updates in real-time.

    Args:
        thread_id: Workflow thread ID
        request: Generation request data
        resume: Whether this is resuming a paused workflow
    """
    try:
        # Try to use real LangGraph workflow
        try:
            from core.orchestration.document_generation_workflow import run_document_generation

            logger.info(
                "using_real_workflow",
                thread_id=thread_id,
                case_id=request.case_id,
            )

            # Get section definitions
            state = await workflow_store.load_state(thread_id)
            sections = state.get("sections", [])

            # Run real LangGraph workflow
            await run_document_generation(
                thread_id=thread_id,
                case_id=request.case_id,
                document_type=request.document_type,
                user_id=request.user_id,
                sections=sections,
            )

        except ImportError:
            # Fallback to mock workflow if imports fail
            logger.warning(
                "falling_back_to_mock_workflow",
                thread_id=thread_id,
                reason="LangGraph workflow imports failed",
            )

            # Load state
            state = await workflow_store.load_state(thread_id)
            if not state:
                logger.error("workflow_bg_no_state", thread_id=thread_id)
                return

            # Check if paused
            if state.get("status") == "paused":
                logger.info("workflow_bg_paused", thread_id=thread_id)
                return

            sections = state.get("sections", [])

            # Process each section (MOCK mode)
            for idx, section in enumerate(sections):
                # Check if paused
                state = await workflow_store.load_state(thread_id)
                if state and state.get("status") == "paused":
                    logger.info(
                        "workflow_bg_paused_during",
                        thread_id=thread_id,
                        section_id=section.get("id"),
                    )
                    return

                # Skip already completed sections (for resume)
                if section.get("status") == "completed":
                    continue

                # Update section to in_progress
                await workflow_store.update_section(
                    thread_id,
                    section.get("id", section.get("section_id")),
                    {"status": "in_progress"},
                )

                # Broadcast WebSocket update
                from core.websocket_manager import broadcast_section_update

                await broadcast_section_update(
                    thread_id,
                    section.get("id", section.get("section_id")),
                    "in_progress",
                )

                # Log progress
                await workflow_store.add_log(
                    thread_id,
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "info",
                        "message": f"Generating section: {section.get('name', section.get('section_name'))}",
                        "agent": "DocumentGenerator",
                    },
                )

                # Simulate generation time (2-5 seconds per section)
                await asyncio.sleep(2 + (idx % 3))

                # Generate mock content
                section_name = section.get("name", section.get("section_name", "Section"))
                mock_content = (
                    f"<h2>{section_name}</h2><p>Generated content for {section_name}...</p>"
                )

                # Update section to completed
                await workflow_store.update_section(
                    thread_id,
                    section.get("id", section.get("section_id")),
                    {
                        "status": "completed",
                        "content_html": mock_content,
                        "tokens_used": 150 + (idx * 50),
                    },
                )

                # Broadcast completion
                await broadcast_section_update(
                    thread_id,
                    section.get("id", section.get("section_id")),
                    "completed",
                    tokens_used=150 + (idx * 50),
                )

            logger.info(
                "section_completed",
                thread_id=thread_id,
                section_id=section.get("id"),
                section_name=section_name,
            )

        # Mark workflow as completed
        await workflow_store.update_workflow_status(thread_id, "completed")

        # Log completion
        await workflow_store.add_log(
            thread_id,
            {
                "timestamp": datetime.now().isoformat(),
                "level": "success",
                "message": "Document generation completed successfully!",
                "agent": "DocumentGenerator",
            },
        )

        logger.info("workflow_completed", thread_id=thread_id)

    except Exception as e:
        logger.error("workflow_bg_error", thread_id=thread_id, error=str(e))

        # Update workflow to error state
        await workflow_store.update_workflow_status(thread_id, "error", error_message=str(e))

        # Log error
        await workflow_store.add_log(
            thread_id,
            {
                "timestamp": datetime.now().isoformat(),
                "level": "error",
                "message": f"Document generation failed: {e!s}",
                "agent": "System",
            },
        )


async def generate_pdf(state: dict[str, Any], thread_id: str) -> Path:
    """
    Generate PDF from document HTML sections.

    Simple implementation using ReportLab or HTML to PDF conversion.

    Args:
        state: Workflow state with sections
        thread_id: Workflow thread ID

    Returns:
        Path to generated PDF file
    """
    try:
        pdf_dir = Path("pdfs")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f"{thread_id}.pdf"

        # Combine all section HTML
        sections = state.get("sections", [])
        html_parts = []

        html_parts.append("<html><head><style>")
        html_parts.append("body { font-family: Arial, sans-serif; margin: 40px; }")
        html_parts.append(
            "h2 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }"
        )
        html_parts.append("</style></head><body>")

        for section in sections:
            if section.get("status") == "completed":
                html_parts.append(section.get("content_html", ""))

        html_parts.append("</body></html>")
        html_content = "\n".join(html_parts)

        # Simple PDF generation using weasyprint (if available) or fallback
        try:
            from weasyprint import HTML

            HTML(string=html_content).write_pdf(pdf_path)
            logger.info("pdf_generated_weasyprint", thread_id=thread_id, path=str(pdf_path))

        except ImportError:
            # Fallback: Write HTML to file instead
            html_path = pdf_dir / f"{thread_id}.html"
            async with aiofiles.open(html_path, "w", encoding="utf-8") as f:
                await f.write(html_content)

            logger.warning(
                "pdf_fallback_html",
                thread_id=thread_id,
                message="weasyprint not available, saved as HTML",
            )

            # Return HTML path instead
            return html_path

        return pdf_path

    except Exception as e:
        logger.error("pdf_generation_error", thread_id=thread_id, error=str(e))
        raise


# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════


@router.websocket("/ws/document/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for real-time document generation updates.

    Replaces polling with push-based updates for better performance.

    Usage:
        const ws = new WebSocket('ws://localhost:8000/api/ws/document/{thread_id}');

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Update:', data);
        };

    Message types:
        - workflow_update: General workflow state changes
        - section_update: Section-specific updates
        - log_entry: New log entries
        - status_change: Overall status changes
        - progress_update: Progress percentage updates
        - error: Error notifications

    Args:
        websocket: WebSocket connection
        thread_id: Workflow thread ID to subscribe to
    """
    await ws_manager.connect(websocket, thread_id)

    try:
        logger.info("websocket_connected", thread_id=thread_id)

        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "thread_id": thread_id,
                "message": "WebSocket connected successfully",
            }
        )

        # Send current state immediately
        state = await workflow_store.load_state(thread_id)
        if state:
            await websocket.send_json(
                {
                    "type": "initial_state",
                    "thread_id": thread_id,
                    "state": state,
                }
            )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (e.g., ping/pong for keep-alive)
                data = await websocket.receive_text()

                # Handle client messages
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                logger.info("websocket_client_disconnect", thread_id=thread_id)
                break

    except Exception as e:
        logger.error("websocket_error", thread_id=thread_id, error=str(e))

    finally:
        ws_manager.disconnect(websocket, thread_id)
        logger.info("websocket_closed", thread_id=thread_id)
