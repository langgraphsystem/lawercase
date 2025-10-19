from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ..memory.models import AuditEvent, MemoryRecord
from ..memory.rmt.buffer import compose_prompt
from .error_handler import check_for_error, handle_error

if TYPE_CHECKING:
    from ..groupagents.case_agent import CaseAgent
    from ..memory.memory_manager import MemoryManager

# Optional imports that may not be available
try:
    from langgraph.checkpoint.memory import MemorySaver  # noqa: F401
    from langgraph.graph import StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


class WorkflowState(BaseModel):
    """State carried through LangGraph workflows (memory + case operations)."""

    model_config = ConfigDict(use_enum_values=True)

    thread_id: str = Field(..., description="Conversation or workflow thread id")
    user_id: str | None = Field(default=None)
    query: str | None = Field(default=None)

    # Inputs/Artifacts
    event: AuditEvent | None = None

    # Case-specific data
    case_id: str | None = Field(default=None, description="Current case ID")
    case_operation: str | None = Field(default=None, description="Requested case operation")
    case_data: dict[str, Any] | None = Field(
        default=None, description="Input payload for case operations"
    )

    # Document workflow data (integrated from legal workflow)
    document_id: str | None = Field(default=None, description="Current document ID")
    document_operation: str | None = Field(default=None, description="Document operation")
    document_data: dict[str, Any] | None = Field(default=None, description="Document data")
    document_content: str | None = Field(default=None, description="Document content")
    is_exhibit: bool = Field(default=False, description="Is this an exhibit document")
    is_draft: bool = Field(default=True, description="Is this a draft document")

    # Validation workflow data
    validation_required: bool = Field(default=True, description="Requires validation")
    validation_level: str = Field(default="standard", description="Validation level")
    validation_results: dict[str, Any] | None = Field(
        default=None, description="Validation results"
    )

    # Feedback workflow data
    feedback_required: bool = Field(default=False, description="Requires peer review")
    feedback_results: dict[str, Any] | None = Field(default=None, description="Feedback results")

    # RAG loop flags (optional)
    needs_rag: bool = Field(default=False, description="Whether to run RAG loop")
    rag_iterations: int = Field(default=1, description="Max RAG loop iterations")

    # Agent results
    case_result: dict[str, Any] | None = Field(
        default=None, description="Result of the CaseAgent execution"
    )
    writer_result: dict[str, Any] | None = Field(
        default=None, description="Result of the WriterAgent execution"
    )
    validator_result: dict[str, Any] | None = Field(
        default=None, description="Result of the ValidatorAgent execution"
    )
    feedback_result: dict[str, Any] | None = Field(
        default=None, description="Result of the FeedbackAgent execution"
    )

    # Outputs/Derived
    reflected: list[MemoryRecord] = Field(default_factory=list)
    retrieved: list[MemoryRecord] = Field(default_factory=list)
    rmt_slots: dict[str, str] = Field(default_factory=dict)

    # Multi-agent coordination hooks
    next_agent: str | None = Field(default=None)
    agent_results: dict[str, Any] = Field(default_factory=dict)

    # Workflow routing
    workflow_step: str = Field(default="start", description="Current workflow step")
    final_output: dict[str, Any] | None = Field(default=None, description="Final workflow output")

    # Error handling
    error: str | None = None

    def model_dump(self, *args, **kwargs):  # type: ignore[override]
        """Serialize with JSON mode for consistent enum handling."""
        if "mode" not in kwargs:
            kwargs["mode"] = "json"
        return super().model_dump(*args, **kwargs)


def _ensure_langgraph() -> None:
    if not LANGGRAPH_AVAILABLE:  # pragma: no cover - import-time guard
        raise ConfigurationError(
            "LangGraph is required for workflow execution. Install with: pip install langgraph",
            details={"missing_package": "langgraph"},
        )


def build_memory_workflow(memory: MemoryManager):
    """Basic memory-oriented workflow used in demos."""

    _ensure_langgraph()
    graph = StateGraph(WorkflowState)

    async def node_log_event(state: WorkflowState) -> WorkflowState:
        if state.event is not None:
            await memory.alog_audit(state.event)
        return state

    async def node_reflect(state: WorkflowState) -> WorkflowState:
        if state.event is not None:
            state.reflected = await memory.awrite(state.event)
        return state

    async def node_retrieve(state: WorkflowState) -> WorkflowState:
        if state.query:
            state.retrieved = await memory.aretrieve(state.query, user_id=state.user_id)
        return state

    async def node_update_rmt(state: WorkflowState) -> WorkflowState:
        persona = ""
        long_term = (
            "\n".join(record.text for record in state.retrieved[:5]) if state.retrieved else ""
        )
        recent = state.reflected[0].text if state.reflected else ""
        slots = {
            "persona": persona,
            "long_term_facts": long_term,
            "open_loops": "",
            "recent_summary": recent,
        }
        state.rmt_slots = slots
        await memory.aset_rmt(state.thread_id, slots)
        _ = compose_prompt(slots)
        return state

    graph.add_node("log_event", node_log_event)
    graph.add_node("reflect", node_reflect)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("update_rmt", node_update_rmt)

    graph.set_entry_point("log_event")
    graph.add_edge("log_event", "reflect")
    graph.add_edge("reflect", "retrieve")
    graph.add_edge("retrieve", "update_rmt")
    graph.set_finish_point("update_rmt")

    return graph


def build_case_workflow(memory: MemoryManager, *, case_agent: CaseAgent | None = None):
    """Workflow that routes case operations through CaseAgent and updates memory."""

    _ensure_langgraph()

    # Runtime import to avoid circular dependency
    from ..groupagents.case_agent import CaseAgent

    agent = case_agent or CaseAgent(memory_manager=memory)
    graph = StateGraph(WorkflowState)

    async def node_case_agent(state: WorkflowState) -> WorkflowState:
        operation = (state.case_operation or "").lower()
        if not operation:
            state.error = "case_operation is required"
            return state

        if not state.user_id:
            state.error = "user_id is required for case operations"
            return state

        payload = state.case_data or {}

        try:
            if operation == "create":
                record = await agent.acreate_case(user_id=state.user_id, case_data=payload)
                state.case_id = record.case_id
                state.case_result = {"operation": "create", "case": record.model_dump()}

            elif operation == "get":
                case_id = state.case_id or payload.get("case_id")
                if not case_id:
                    raise ValidationError("case_id is required for get operation", field="case_id")
                record = await agent.aget_case(case_id=case_id, user_id=state.user_id)
                state.case_id = record.case_id
                state.case_result = {"operation": "get", "case": record.model_dump()}

            elif operation == "update":
                case_id = state.case_id or payload.get("case_id")
                if not case_id:
                    raise ValidationError(
                        "case_id is required for update operation", field="case_id"
                    )
                updates_payload = payload.get("updates")
                if updates_payload is None:
                    updates = {k: v for k, v in payload.items() if k != "case_id"}
                else:
                    updates = dict(updates_payload)
                record = await agent.aupdate_case(
                    case_id=case_id, updates=updates, user_id=state.user_id
                )
                state.case_id = record.case_id
                state.case_result = {"operation": "update", "case": record.model_dump()}

            elif operation == "delete":
                case_id = state.case_id or payload.get("case_id")
                if not case_id:
                    raise ValidationError(
                        "case_id is required for delete operation", field="case_id"
                    )
                result = await agent.adelete_case(case_id=case_id, user_id=state.user_id)
                state.case_result = {"operation": "delete", "result": result.model_dump()}

            elif operation == "search":
                # Runtime import to avoid circular dependency
                from ..groupagents.models import CaseQuery

                query = CaseQuery(**payload)
                cases = await agent.asearch_cases(query=query, user_id=state.user_id)
                state.case_result = {
                    "operation": "search",
                    "cases": [case.model_dump() for case in cases],
                    "count": len(cases),
                }

            elif operation == "start_workflow":
                case_id = state.case_id or payload.get("case_id")
                if not case_id:
                    raise ValidationError(
                        "case_id is required for start_workflow operation", field="case_id"
                    )
                result = await agent.astart_workflow(case_id=case_id, user_id=state.user_id)
                state.case_id = case_id
                state.case_result = {"operation": "start_workflow", "workflow": result}

            else:
                raise WorkflowError(
                    f"Unsupported case operation: {operation}", workflow_name="case_workflow"
                )

            state.agent_results["case_agent"] = state.case_result

        except Exception as exc:  # pragma: no cover - defensive
            state.error = str(exc)
            state.case_result = {"operation": operation, "error": str(exc)}

        return state

    async def node_audit(state: WorkflowState) -> WorkflowState:
        if state.event is not None:
            await memory.alog_audit(state.event)

        if state.case_result and state.user_id:
            audit_event = AuditEvent(
                event_id=str(uuid4()),
                user_id=state.user_id,
                thread_id=state.thread_id,
                source="case_workflow",
                action=f"case_{state.case_operation or 'operation'}",
                payload=state.case_result,
                tags=["case", "workflow"],
            )
            await memory.alog_audit(audit_event)

        return state

    async def node_reflect(state: WorkflowState) -> WorkflowState:
        reflections: list[MemoryRecord] = []

        if state.event is not None:
            reflections.extend(await memory.awrite(state.event))

        if state.case_result and state.user_id:
            parts = [f"case:{state.case_operation}" if state.case_operation else "case"]
            if state.case_id:
                parts.append(f"id={state.case_id}")
            case_payload = (
                state.case_result.get("case") if isinstance(state.case_result, dict) else None
            )
            if isinstance(case_payload, dict):
                title = case_payload.get("title")
                if title:
                    parts.append(f"title={title}")
            summary = " | ".join(parts)

            record = MemoryRecord(
                user_id=state.user_id,
                text=summary,
                source="case_workflow",
                tags=[tag for tag in ["case", state.case_operation] if tag],
            )
            reflections.extend(await memory.awrite([record]))

        state.reflected = reflections
        return state

    async def node_retrieve(state: WorkflowState) -> WorkflowState:
        query = state.query
        if not query and state.case_id:
            query = state.case_id
        if query:
            state.retrieved = await memory.aretrieve(query, user_id=state.user_id)
        return state

    async def node_update_rmt(state: WorkflowState) -> WorkflowState:
        persona = ""
        long_term = (
            "\n".join(record.text for record in state.retrieved[:5]) if state.retrieved else ""
        )

        summary = ""
        if isinstance(state.case_result, dict):
            operation = state.case_result.get("operation")
            if operation:
                summary = f"Case operation: {operation}"
            if state.case_id:
                summary += f" (ID: {state.case_id})"
        if not summary and state.reflected:
            summary = state.reflected[0].text

        slots = {
            "persona": persona,
            "long_term_facts": long_term,
            "open_loops": "",
            "recent_summary": summary,
        }
        state.rmt_slots = slots
        await memory.aset_rmt(state.thread_id, slots)
        _ = compose_prompt(slots)
        return state

    graph.add_node("case_agent", node_case_agent)
    graph.add_node("audit", node_audit)
    graph.add_node("reflect", node_reflect)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("update_rmt", node_update_rmt)

    graph.set_entry_point("case_agent")
    graph.add_edge("case_agent", "audit")
    graph.add_edge("audit", "reflect")
    graph.add_edge("reflect", "retrieve")
    graph.add_edge("retrieve", "update_rmt")
    graph.set_finish_point("update_rmt")

    return graph


def build_advanced_case_workflow(memory: MemoryManager, *, case_agent: CaseAgent | None = None):
    """Advanced case workflow with optional RAG/CAG/KAG/MAGCC/RAC loop and error routing."""
    _ensure_langgraph()

    from ..groupagents.case_agent import CaseAgent

    agent = case_agent or CaseAgent(memory_manager=memory)
    graph = StateGraph(WorkflowState)

    async def node_case_agent(state: WorkflowState) -> WorkflowState:
        # Reuse basic handler by delegating to existing workflow via function call-like behavior
        inner = build_case_workflow(memory, case_agent=agent)
        compiled = inner.compile()
        # Replay state through inner workflow quickly
        final: WorkflowState | None = None
        async for step in compiled.astream(
            state, config={"configurable": {"thread_id": state.thread_id}}
        ):
            final = step
        return final or state

    async def node_rag(state: WorkflowState) -> WorkflowState:
        if state.query:
            state.retrieved = await memory.aretrieve(state.query, user_id=state.user_id)
        return state

    async def node_cag(state: WorkflowState) -> WorkflowState:
        content = "\n".join(r.text for r in state.retrieved[:5]) if state.retrieved else ""
        state.rmt_slots["long_term_facts"] = content
        return state

    async def node_kag(state: WorkflowState) -> WorkflowState:
        return state

    async def node_magcc(state: WorkflowState) -> WorkflowState:
        state.agent_results["magcc_score"] = 0.9
        return state

    async def node_rac_conversation(state: WorkflowState) -> WorkflowState:
        return state

    async def node_rac_correction(state: WorkflowState) -> WorkflowState:
        # Decrease remaining iterations
        if state.rag_iterations > 0:
            state.rag_iterations -= 1
        return state

    async def node_error_check(state: WorkflowState) -> WorkflowState:
        if check_for_error(state):
            return await handle_error(state)
        return state

    graph.add_node("case_agent", node_case_agent)
    graph.add_node("error_check", node_error_check)
    graph.add_node("rag", node_rag)
    graph.add_node("cag", node_cag)
    graph.add_node("kag", node_kag)
    graph.add_node("magcc", node_magcc)
    graph.add_node("rac_conversation", node_rac_conversation)
    graph.add_node("rac_correction", node_rac_correction)

    graph.set_entry_point("case_agent")
    graph.add_edge("case_agent", "error_check")

    # Try to use conditional edges if available
    try:
        graph.add_conditional_edges(
            "error_check",
            lambda s: "rag" if getattr(s, "needs_rag", False) else "end",
            {"rag": "rag", "end": "end"},
        )
        graph.add_edge("rag", "cag")
        graph.add_edge("cag", "kag")
        graph.add_edge("kag", "magcc")
        graph.add_edge("magcc", "rac_conversation")
        graph.add_edge("rac_conversation", "rac_correction")
        graph.add_conditional_edges(
            "rac_correction",
            lambda s: "rag" if getattr(s, "rag_iterations", 0) > 0 else "end",
            {"rag": "rag", "end": "end"},
        )
    except Exception:
        # Fallback linear chain
        graph.add_edge("error_check", "rag")
        graph.add_edge("rag", "cag")
        graph.add_edge("cag", "kag")
        graph.add_edge("kag", "magcc")
        graph.add_edge("magcc", "rac_conversation")
        graph.add_edge("rac_conversation", "rac_correction")
        graph.set_finish_point("rac_correction")
    else:
        graph.set_finish_point("rac_correction")

    return graph


# Import the legal document workflow from the dedicated module
try:
    from .legal_workflow import build_legal_document_workflow
except ImportError:
    # Fallback if legal_workflow module is not available
    def build_legal_document_workflow(*_args, **_kwargs):
        raise WorkflowError(
            "Legal document workflow not available - missing legal_workflow module",
            workflow_name="legal_document",
            details={"reason": "missing_module"},
        )


# ========== EB-1A COMPLETE WORKFLOW ==========


def build_eb1a_complete_workflow(memory: MemoryManager):
    """
    Complete EB-1A petition workflow with evidence analysis and validation.

    Workflow stages:
    1. validate_eligibility - Check minimum requirements (3+ criteria)
    2. gather_evidence - Collect all evidence from case
    3. analyze_evidence - EB1AEvidenceAnalyzer for each evidence
    4. evaluate_criteria - Evaluate each criterion
    5. calculate_strength - Overall case strength
    6. identify_gaps - Find missing evidence
    7. generate_recommendations - Improvement recommendations
    8. generate_documents - Generate petition if ready
    9. validate_petition - Validate with ValidatorAgent
    10. human_review - Interrupt point for human
    11. finalize - Final preparation

    Conditional routing:
    - After validate_eligibility: proceed/insufficient/need_more_info
    - After calculate_strength: ready_to_file/needs_improvement/not_ready
    - After validate_petition: approved/needs_revision
    - After human_review: approve/revise/reject
    """
    _ensure_langgraph()

    from ..groupagents.eb1a_evidence_analyzer import EB1AEvidenceAnalyzer
    from ..groupagents.validator_agent import (ValidationLevel,
                                               ValidationRequest,
                                               ValidatorAgent)
    from ..workflows.eb1a.eb1a_coordinator import EB1ACriterion

    analyzer = EB1AEvidenceAnalyzer(memory_manager=memory)
    validator = ValidatorAgent(memory_manager=memory)

    graph = StateGraph(WorkflowState)

    # === NODE 1: Validate Eligibility ===
    async def node_validate_eligibility(state: WorkflowState) -> WorkflowState:
        """Check if case meets minimum EB-1A requirements."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_validate_eligibility", case_id=state.case_id)

        payload = state.case_data or {}
        criteria = payload.get("criteria", [])
        evidence_count = len(payload.get("evidence", []))

        # Check minimum requirements
        meets_criteria = len(criteria) >= 3
        has_evidence = evidence_count >= 5

        state.agent_results["eligibility"] = {
            "meets_criteria_minimum": meets_criteria,
            "criteria_count": len(criteria),
            "evidence_count": evidence_count,
            "has_sufficient_evidence": has_evidence,
            "decision": (
                "proceed"
                if (meets_criteria and has_evidence)
                else "insufficient" if not meets_criteria else "need_more_info"
            ),
        }

        # Audit log
        await memory.alog_audit(
            AuditEvent(
                event_id=str(uuid4()),
                user_id=state.user_id or "system",
                thread_id=state.thread_id,
                source="eb1a_workflow",
                action="validate_eligibility",
                payload=state.agent_results["eligibility"],
                tags=["eb1a", "eligibility"],
            )
        )

        state.workflow_step = "eligibility_validated"
        return state

    # === NODE 2: Gather Evidence ===
    async def node_gather_evidence(state: WorkflowState) -> WorkflowState:
        """Gather all evidence items from case data."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_gather_evidence", case_id=state.case_id)

        from ..workflows.eb1a.eb1a_coordinator import EB1AEvidence

        payload = state.case_data or {}
        evidence_list = []

        for ev_data in payload.get("evidence", []):
            if isinstance(ev_data, dict):
                evidence_list.append(EB1AEvidence(**ev_data))
            else:
                evidence_list.append(ev_data)

        state.agent_results["evidence_list"] = evidence_list
        state.agent_results["evidence_count"] = len(evidence_list)

        state.workflow_step = "evidence_gathered"
        return state

    # === NODE 3: Analyze Evidence ===
    async def node_analyze_evidence(state: WorkflowState) -> WorkflowState:
        """Analyze each evidence item using EB1AEvidenceAnalyzer."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_analyze_evidence")

        evidence_list = state.agent_results.get("evidence_list", [])
        analyses = []

        for evidence in evidence_list:
            analysis = await analyzer.analyze_evidence(evidence)
            analyses.append(analysis)

        state.agent_results["evidence_analyses"] = analyses
        state.agent_results["avg_evidence_score"] = (
            sum(a.quality_metrics.strength_score for a in analyses) / len(analyses)
            if analyses
            else 0.0
        )

        state.workflow_step = "evidence_analyzed"
        return state

    # === NODE 4: Evaluate Criteria ===
    async def node_evaluate_criteria(state: WorkflowState) -> WorkflowState:
        """Evaluate satisfaction of each EB-1A criterion."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_evaluate_criteria")

        payload = state.case_data or {}
        criteria = payload.get("criteria", [])
        evidence_list = state.agent_results.get("evidence_list", [])

        # Group evidence by criterion
        evidence_by_criterion = {}
        for evidence in evidence_list:
            criterion = evidence.criterion
            if criterion not in evidence_by_criterion:
                evidence_by_criterion[criterion] = []
            evidence_by_criterion[criterion].append(evidence)

        # Evaluate each criterion
        criterion_evaluations = {}
        for criterion_value in criteria:
            try:
                criterion = EB1ACriterion(criterion_value)
                ev_list = evidence_by_criterion.get(criterion, [])
                evaluation = await analyzer.evaluate_criterion_satisfaction(criterion, ev_list)
                criterion_evaluations[criterion.value] = evaluation
            except Exception as e:
                logger.error("criterion_eval_error", criterion=criterion_value, error=str(e))

        state.agent_results["criterion_evaluations"] = criterion_evaluations
        state.workflow_step = "criteria_evaluated"
        return state

    # === NODE 5: Calculate Strength ===
    async def node_calculate_strength(state: WorkflowState) -> WorkflowState:
        """Calculate overall case strength."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_calculate_strength")

        payload = state.case_data or {}
        criteria = payload.get("criteria", [])
        evidence_list = state.agent_results.get("evidence_list", [])

        # Group evidence by criterion
        evidence_by_criterion = {}
        for evidence in evidence_list:
            criterion = evidence.criterion
            if criterion not in evidence_by_criterion:
                evidence_by_criterion[criterion] = []
            evidence_by_criterion[criterion].append(evidence)

        # Calculate case strength
        case_analysis = await analyzer.calculate_case_strength(evidence_by_criterion)

        state.agent_results["case_strength"] = case_analysis
        state.agent_results["readiness_decision"] = (
            "ready_to_file"
            if case_analysis.overall_score >= 80 and case_analysis.meets_minimum_criteria
            else "needs_improvement" if case_analysis.overall_score >= 60 else "not_ready"
        )

        # Audit log
        await memory.alog_audit(
            AuditEvent(
                event_id=str(uuid4()),
                user_id=state.user_id or "system",
                thread_id=state.thread_id,
                source="eb1a_workflow",
                action="calculate_strength",
                payload={
                    "score": case_analysis.overall_score,
                    "decision": state.agent_results["readiness_decision"],
                },
                tags=["eb1a", "strength"],
            )
        )

        state.workflow_step = "strength_calculated"
        return state

    # === NODE 6: Identify Gaps ===
    async def node_identify_gaps(state: WorkflowState) -> WorkflowState:
        """Identify missing evidence and weak areas."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_identify_gaps")

        case_strength = state.agent_results.get("case_strength")
        if not case_strength:
            state.workflow_step = "gaps_identified"
            return state

        gaps = {
            "missing_criteria": [
                c for c in EB1ACriterion if c not in case_strength.criterion_evaluations
            ][
                :3
            ],  # Top 3
            "weak_criteria": [
                k for k, v in case_strength.criterion_evaluations.items() if not v.is_satisfied
            ],
            "risks": case_strength.risks,
            "critical_issues": [
                risk for risk in case_strength.risks if "CRITICAL" in risk or "critical" in risk
            ],
        }

        state.agent_results["gaps"] = gaps
        state.workflow_step = "gaps_identified"
        return state

    # === NODE 7: Generate Recommendations ===
    async def node_generate_recommendations(state: WorkflowState) -> WorkflowState:
        """Generate improvement recommendations."""
        case_strength = state.agent_results.get("case_strength")
        gaps = state.agent_results.get("gaps", {})

        recommendations = []

        if case_strength:
            recommendations.extend(case_strength.priority_recommendations[:3])
            recommendations.extend(case_strength.secondary_recommendations[:2])

        # Add gap-based recommendations
        if gaps.get("critical_issues"):
            recommendations.insert(
                0, f"URGENT: Address {len(gaps['critical_issues'])} critical issues"
            )

        state.agent_results["recommendations"] = recommendations
        state.workflow_step = "recommendations_generated"
        return state

    # === NODE 8: Generate Documents ===
    async def node_generate_documents(state: WorkflowState) -> WorkflowState:
        """Generate petition documents if ready."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_generate_documents")

        decision = state.agent_results.get("readiness_decision")

        if decision == "ready_to_file":
            # Generate petition document (placeholder)
            state.agent_results["documents_generated"] = True
            state.agent_results["petition_content"] = "# EB-1A Petition\n\n[Generated content...]"
        else:
            state.agent_results["documents_generated"] = False
            state.agent_results["skip_reason"] = f"Not ready: {decision}"

        state.workflow_step = "documents_generated"
        return state

    # === NODE 9: Validate Petition ===
    async def node_validate_petition(state: WorkflowState) -> WorkflowState:
        """Validate petition with ValidatorAgent."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_validate_petition")

        if not state.agent_results.get("documents_generated"):
            state.agent_results["validation_skipped"] = True
            state.workflow_step = "validation_skipped"
            return state

        petition_content = state.agent_results.get("petition_content", "")

        # Validate with ValidatorAgent
        request = ValidationRequest(
            document_id=str(uuid4()),
            content=petition_content,
            document_type="eb1a_petition",
            validation_level=ValidationLevel.STRICT,
            user_id=state.user_id or "system",
        )

        validation_result = await validator.avalidate(request)

        state.agent_results["petition_validation"] = validation_result
        state.agent_results["validation_decision"] = (
            "approved"
            if validation_result.is_valid and (validation_result.score or 0) >= 0.8
            else "needs_revision"
        )

        state.workflow_step = "petition_validated"
        return state

    # === NODE 10: Human Review ===
    async def node_human_review(state: WorkflowState) -> WorkflowState:
        """Interrupt point for human review."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_human_review")

        # Set interrupt flag
        state.agent_results["awaiting_human_review"] = True
        state.agent_results["human_decision"] = "pending"  # Will be set by human

        state.workflow_step = "human_review"
        return state

    # === NODE 11: Finalize ===
    async def node_finalize(state: WorkflowState) -> WorkflowState:
        """Finalize petition for filing."""
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("eb1a_finalize")

        case_strength = state.agent_results.get("case_strength")
        final_output = {
            "status": "finalized",
            "case_id": state.case_id,
            "overall_score": case_strength.overall_score if case_strength else 0,
            "ready_for_filing": state.agent_results.get("readiness_decision") == "ready_to_file",
            "documents_generated": state.agent_results.get("documents_generated", False),
            "human_approved": state.agent_results.get("human_decision") == "approve",
            "recommendations": state.agent_results.get("recommendations", []),
        }

        state.final_output = final_output
        state.workflow_step = "finalized"

        # Final audit log
        await memory.alog_audit(
            AuditEvent(
                event_id=str(uuid4()),
                user_id=state.user_id or "system",
                thread_id=state.thread_id,
                source="eb1a_workflow",
                action="finalize",
                payload=final_output,
                tags=["eb1a", "finalize"],
            )
        )

        return state

    # === ROUTING FUNCTIONS ===
    def route_after_eligibility(state: WorkflowState) -> str:
        decision = state.agent_results.get("eligibility", {}).get("decision", "insufficient")
        if decision == "proceed":
            return "gather_evidence"
        if decision == "insufficient":
            return "finalize"  # End workflow
        # need_more_info
        return "finalize"

    def route_after_strength(state: WorkflowState) -> str:
        decision = state.agent_results.get("readiness_decision", "not_ready")
        return "identify_gaps"  # Always go to gaps first

    def route_after_documents(state: WorkflowState) -> str:
        if state.agent_results.get("documents_generated"):
            return "validate_petition"
        return "human_review"  # Skip validation if no documents

    def route_after_validation(state: WorkflowState) -> str:
        if state.agent_results.get("validation_skipped"):
            return "human_review"
        decision = state.agent_results.get("validation_decision", "needs_revision")
        return "human_review"  # Always go to human review

    def route_after_human_review(state: WorkflowState) -> str:
        decision = state.agent_results.get("human_decision", "pending")
        if decision == "approve":
            return "finalize"
        if decision == "revise":
            return "identify_gaps"  # Loop back
        # reject or pending
        return "finalize"

    # === BUILD GRAPH ===
    graph.add_node("validate_eligibility", node_validate_eligibility)
    graph.add_node("gather_evidence", node_gather_evidence)
    graph.add_node("analyze_evidence", node_analyze_evidence)
    graph.add_node("evaluate_criteria", node_evaluate_criteria)
    graph.add_node("calculate_strength", node_calculate_strength)
    graph.add_node("identify_gaps", node_identify_gaps)
    graph.add_node("generate_recommendations", node_generate_recommendations)
    graph.add_node("generate_documents", node_generate_documents)
    graph.add_node("validate_petition", node_validate_petition)
    graph.add_node("human_review", node_human_review)
    graph.add_node("finalize", node_finalize)

    # Set entry point
    graph.set_entry_point("validate_eligibility")

    # Add conditional edges
    graph.add_conditional_edges(
        "validate_eligibility",
        route_after_eligibility,
        {
            "gather_evidence": "gather_evidence",
            "finalize": "finalize",
        },
    )

    # Linear flow through analysis
    graph.add_edge("gather_evidence", "analyze_evidence")
    graph.add_edge("analyze_evidence", "evaluate_criteria")
    graph.add_edge("evaluate_criteria", "calculate_strength")

    graph.add_conditional_edges(
        "calculate_strength", route_after_strength, {"identify_gaps": "identify_gaps"}
    )

    graph.add_edge("identify_gaps", "generate_recommendations")
    graph.add_edge("generate_recommendations", "generate_documents")

    graph.add_conditional_edges(
        "generate_documents",
        route_after_documents,
        {
            "validate_petition": "validate_petition",
            "human_review": "human_review",
        },
    )

    graph.add_conditional_edges(
        "validate_petition", route_after_validation, {"human_review": "human_review"}
    )

    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "finalize": "finalize",
            "identify_gaps": "identify_gaps",
        },
    )

    # Set finish point
    graph.set_finish_point("finalize")

    return graph
