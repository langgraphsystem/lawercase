"""
Legal Document Workflow - Comprehensive workflow for legal document generation.

Implements the 8-step legal document workflow with conditional logic:
1. Case setup and document initiation
2. Document generation (Writer Agent)
3. Validation cycle (Validator Agent)
4. Feedback cycle (Feedback Agent) - optional
5. Conditional logic for exhibits vs drafts
6. Final approval and PDF generation
7. Audit trail and memory updates
8. Workflow completion
"""

from __future__ import annotations

from uuid import uuid4

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent, MemoryRecord
from .workflow_graph import WorkflowState, _ensure_langgraph

# Optional imports that may not be available
try:
    from langgraph.graph import StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

if TYPE_CHECKING:
    from ..groupagents.case_agent import CaseAgent
    from ..groupagents.feedback_agent import FeedbackAgent
    from ..groupagents.validator_agent import ValidatorAgent
    from ..groupagents.writer_agent import WriterAgent


def build_legal_document_workflow(
    memory: MemoryManager,
    *,
    case_agent: CaseAgent | None = None,
    writer_agent: WriterAgent | None = None,
    validator_agent: ValidatorAgent | None = None,
    feedback_agent: FeedbackAgent | None = None,
):
    """
    Comprehensive workflow for legal document generation with validation and feedback.

    Implements the 8-step legal document workflow:
    1. Case setup and document initiation
    2. Document generation (Writer Agent)
    3. Validation cycle (Validator Agent)
    4. Feedback cycle (Feedback Agent) - optional
    5. Conditional logic for exhibits vs drafts
    6. Final approval and PDF generation
    7. Audit trail and memory updates
    8. Workflow completion
    """

    _ensure_langgraph()

    # Runtime imports to avoid circular dependencies
    from ..groupagents.case_agent import CaseAgent
    from ..groupagents.feedback_agent import FeedbackAgent, FeedbackRequest
    from ..groupagents.validator_agent import (ValidationLevel,
                                               ValidationRequest,
                                               ValidatorAgent)
    from ..groupagents.writer_agent import (DocumentFormat, DocumentRequest,
                                            DocumentType, WriterAgent)

    # Initialize agents
    case_agent_instance = case_agent or CaseAgent(memory_manager=memory)
    writer_agent_instance = writer_agent or WriterAgent(memory_manager=memory)
    validator_agent_instance = validator_agent or ValidatorAgent(memory_manager=memory)
    feedback_agent_instance = feedback_agent or FeedbackAgent(memory_manager=memory)

    graph = StateGraph(WorkflowState)

    # Step 1: Case Setup
    async def node_case_setup(state: WorkflowState) -> WorkflowState:
        """Setup case context for document workflow"""
        if not state.case_id or not state.user_id:
            state.error = "case_id and user_id are required"
            return state

        try:
            # Get case details
            case_record = await case_agent_instance.aget_case(state.case_id, state.user_id)
            state.case_result = {"case": case_record.model_dump()}
            state.workflow_step = "document_generation"

        except Exception as exc:
            state.error = f"Case setup failed: {exc!s}"

        return state

    # Step 2: Document Generation
    async def node_document_generation(state: WorkflowState) -> WorkflowState:
        """Generate document using WriterAgent"""
        if state.error:
            return state

        try:
            # Prepare document request
            document_data = state.document_data or {}

            # Determine document type based on case context
            doc_type = DocumentType.LETTER
            if state.is_exhibit:
                doc_type = DocumentType.BRIEF
            elif document_data.get("type") == "contract":
                doc_type = DocumentType.CONTRACT

            request = DocumentRequest(
                document_type=doc_type,
                content_data=document_data,
                format=DocumentFormat.MARKDOWN,
                case_id=state.case_id,
                approval_required=not state.is_exhibit,  # Exhibits need less approval
            )

            # Generate document
            document = await writer_agent_instance.agenerate_letter(request, state.user_id)

            state.document_id = document.document_id
            state.document_content = document.content
            state.writer_result = {"document": document.model_dump()}
            state.workflow_step = "validation"

        except Exception as exc:
            state.error = f"Document generation failed: {exc!s}"

        return state

    # Step 3: Validation
    async def node_validation(state: WorkflowState) -> WorkflowState:
        """Validate document using ValidatorAgent"""
        if state.error or not state.validation_required:
            state.workflow_step = "feedback_check"
            return state

        try:
            # Determine validation level based on document type
            validation_level = ValidationLevel.STANDARD
            if state.is_exhibit:
                validation_level = ValidationLevel.BASIC
            elif state.validation_level == "strict":
                validation_level = ValidationLevel.STRICT

            request = ValidationRequest(
                document_id=state.document_id,
                content=state.document_content or "",
                document_type=state.document_data.get("type", "letter"),
                validation_level=validation_level,
                case_id=state.case_id,
                user_id=state.user_id,
            )

            # Perform validation
            report = await validator_agent_instance.avalidate_document(request)

            state.validation_results = report.model_dump()
            state.validator_result = {"report": report.model_dump()}
            state.workflow_step = "feedback_check"

        except Exception as exc:
            state.error = f"Validation failed: {exc!s}"

        return state

    # Step 4: Feedback Check (Conditional)
    async def node_feedback_check(state: WorkflowState) -> WorkflowState:
        """Determine if feedback is needed"""
        if state.error:
            return state

        # Skip feedback for exhibits or if not required
        if state.is_exhibit or not state.feedback_required:
            state.workflow_step = "document_finalization"
        else:
            state.workflow_step = "feedback_collection"

        return state

    # Step 5: Feedback Collection (Optional)
    async def node_feedback_collection(state: WorkflowState) -> WorkflowState:
        """Collect feedback using FeedbackAgent"""
        if state.error or state.workflow_step != "feedback_collection":
            return state

        try:
            # Create feedback request
            request = FeedbackRequest(
                document_id=state.document_id,
                requester_id=state.user_id,
                reviewer_ids=[state.user_id],  # In real scenario, get actual reviewers
                case_id=state.case_id,
            )

            # Request feedback
            feedback_request = await feedback_agent_instance.arequest_feedback(
                request, state.user_id
            )

            state.feedback_result = {"request": feedback_request.model_dump()}
            state.workflow_step = "document_finalization"

        except Exception as exc:
            state.error = f"Feedback collection failed: {exc!s}"

        return state

    # Step 6: Document Finalization
    async def node_document_finalization(state: WorkflowState) -> WorkflowState:
        """Finalize document and generate PDF if needed"""
        if state.error:
            return state

        try:
            final_document = {}

            # Check validation results
            if state.validation_results:
                validation_passed = state.validation_results.get("overall_result", {}).get(
                    "is_valid", False
                )
                if not validation_passed and not state.is_exhibit:
                    state.error = "Document validation failed - cannot finalize"
                    return state

            # Generate PDF for final documents
            if not state.is_draft and state.document_id:
                pdf_path = await writer_agent_instance.agenerate_document_pdf(
                    state.document_id, state.user_id
                )
                final_document["pdf_path"] = pdf_path

            final_document.update(
                {
                    "document_id": state.document_id,
                    "case_id": state.case_id,
                    "validation_passed": state.validation_results.get("overall_result", {}).get(
                        "is_valid", True
                    ),
                    "feedback_collected": state.feedback_result is not None,
                    "is_exhibit": state.is_exhibit,
                    "is_draft": state.is_draft,
                }
            )

            state.final_output = final_document
            state.workflow_step = "audit_and_memory"

        except Exception as exc:
            state.error = f"Document finalization failed: {exc!s}"

        return state

    # Step 7: Audit and Memory Update
    async def node_audit_and_memory(state: WorkflowState) -> WorkflowState:
        """Update audit trail and memory"""
        if state.error:
            return state

        try:
            # Create comprehensive audit event
            audit_event = AuditEvent(
                event_id=str(uuid4()),
                user_id=state.user_id,
                thread_id=state.thread_id,
                source="legal_document_workflow",
                action="document_workflow_completed",
                payload={
                    "case_id": state.case_id,
                    "document_id": state.document_id,
                    "workflow_step": state.workflow_step,
                    "validation_passed": (
                        state.validation_results.get("overall_result", {}).get("is_valid", True)
                        if state.validation_results
                        else True
                    ),
                    "feedback_collected": state.feedback_result is not None,
                    "final_output": state.final_output,
                },
                tags=["legal_workflow", "document_generation", "validation", "feedback"],
            )
            await memory.alog_audit(audit_event)

            # Update memory with workflow summary
            summary = f"Legal document workflow completed for case {state.case_id}"
            if state.document_id:
                summary += f", generated document {state.document_id}"
            if state.validation_results:
                validation_score = state.validation_results.get("overall_result", {}).get(
                    "score", 0
                )
                summary += f", validation score: {validation_score:.2f}"

            record = MemoryRecord(
                user_id=state.user_id,
                text=summary,
                source="legal_document_workflow",
                tags=["workflow_completion", "legal_document"],
                metadata={
                    "case_id": state.case_id,
                    "document_id": state.document_id,
                    "workflow_success": state.error is None,
                },
            )

            reflections = await memory.awrite([record])
            state.reflected = reflections
            state.workflow_step = "completed"

        except Exception as exc:
            state.error = f"Audit and memory update failed: {exc!s}"

        return state

    # Add nodes to graph
    graph.add_node("case_setup", node_case_setup)
    graph.add_node("document_generation", node_document_generation)
    graph.add_node("validation", node_validation)
    graph.add_node("feedback_check", node_feedback_check)
    graph.add_node("feedback_collection", node_feedback_collection)
    graph.add_node("document_finalization", node_document_finalization)
    graph.add_node("audit_and_memory", node_audit_and_memory)

    # Define workflow edges
    graph.set_entry_point("case_setup")
    graph.add_edge("case_setup", "document_generation")
    graph.add_edge("document_generation", "validation")
    graph.add_edge("validation", "feedback_check")

    # Conditional routing from feedback_check
    def route_from_feedback_check(state: WorkflowState) -> str:
        if state.workflow_step == "feedback_collection":
            return "feedback_collection"
        return "document_finalization"

    graph.add_conditional_edges(
        "feedback_check",
        route_from_feedback_check,
        {
            "feedback_collection": "feedback_collection",
            "document_finalization": "document_finalization",
        },
    )

    graph.add_edge("feedback_collection", "document_finalization")
    graph.add_edge("document_finalization", "audit_and_memory")
    graph.set_finish_point("audit_and_memory")

    return graph
