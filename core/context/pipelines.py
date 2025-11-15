"""Context pipelines for different agent types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
import logging
from typing import Any

from .context_manager import ContextBlock, ContextManager, ContextTemplate, ContextType

logger = logging.getLogger(__name__)


class ContextPipelineType(str, Enum):
    """Types of context pipelines."""

    CASE_AGENT = "case_agent"
    WRITER_AGENT = "writer_agent"
    VALIDATOR_AGENT = "validator_agent"
    SUPERVISOR_AGENT = "supervisor_agent"
    RAG_PIPELINE = "rag_pipeline"
    LEGAL_RESEARCH = "legal_research"
    DEFAULT = "default"


class ContextPipeline(ABC):
    """Base class for context pipelines."""

    def __init__(self, context_manager: ContextManager) -> None:
        """Initialize pipeline.

        Args:
            context_manager: ContextManager instance to use
        """
        self.context_manager = context_manager
        self.setup_templates()

    @abstractmethod
    def setup_templates(self) -> None:
        """Setup agent-specific templates."""

    @abstractmethod
    def build_context(self, **kwargs: Any) -> str:
        """Build context for the agent.

        Args:
            **kwargs: Agent-specific parameters

        Returns:
            Optimized context string
        """


class CaseAgentPipeline(ContextPipeline):
    """Context pipeline for Case Agent."""

    def setup_templates(self) -> None:
        """Setup Case Agent templates."""
        template = ContextTemplate(
            name="case_agent",
            description="Context template for case management agent",
            template="""You are a Case Management Agent specialized in legal case handling.

**Current Task:** {task}

**Your Responsibilities:**
- Create, read, update, and delete case records
- Maintain case metadata and versions
- Ensure data consistency and optimistic locking
- Track case history and changes

**Available Operations:**
- create_case: Create a new case with client and legal information
- get_case: Retrieve case details by ID
- update_case: Update existing case (with version control)
- search_cases: Find cases by various criteria
- list_recent_cases: Get recent case activity

**Guidelines:**
- Always verify case_id before operations
- Use optimistic locking for updates (check version)
- Log all case modifications
- Validate required fields before creation
- Provide clear error messages

{additional_context}""",
            max_tokens=2000,
            priority=10,
            required_fields=["task"],
            optional_fields=["additional_context"],
            context_type=ContextType.SYSTEM,
        )
        self.context_manager.register_template(template)

    def build_context(
        self,
        task: str,
        case_history: list[dict[str, Any]] | None = None,
        recent_cases: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        """Build context for Case Agent.

        Args:
            task: Current task description
            case_history: Recent case history
            recent_cases: List of recent case summaries
            **kwargs: Additional parameters

        Returns:
            Optimized context
        """
        additional_blocks = []

        if case_history:
            history_content = "Recent Case History:\n" + "\n".join(
                f"- {h.get('action', 'unknown')}: Case {h.get('case_id', 'N/A')}"
                for h in case_history[-5:]  # Last 5 actions
            )
            additional_blocks.append(
                ContextBlock(
                    content=history_content,
                    context_type=ContextType.BACKGROUND,
                    priority=7,
                    source="case_history",
                )
            )

        if recent_cases:
            cases_content = "Recent Cases:\n" + "\n".join(recent_cases[:10])
            additional_blocks.append(
                ContextBlock(
                    content=cases_content,
                    context_type=ContextType.BACKGROUND,
                    priority=6,
                    source="recent_cases",
                )
            )

        return self.context_manager.build_context(
            template_name="case_agent",
            additional_context=additional_blocks,
            task=task,
        )


class WriterAgentPipeline(ContextPipeline):
    """Context pipeline for Writer Agent."""

    def setup_templates(self) -> None:
        """Setup Writer Agent templates."""
        template = ContextTemplate(
            name="writer_agent",
            description="Context template for document generation agent",
            template="""You are a Document Generation Agent specialized in legal writing.

**Current Task:** {task}

**Your Capabilities:**
- Generate legal letters and documents
- Apply appropriate templates and styles
- Ensure legal terminology accuracy
- Format documents professionally
- Support multiple languages

**Document Types:**
- Legal letters (demand, notice, response)
- Contracts and agreements
- Legal memoranda
- Court filings
- Client correspondence

**Quality Standards:**
- Clear and professional language
- Proper legal citations
- Consistent formatting
- Accurate factual information
- Appropriate tone and formality

{style_guide}

{templates_info}""",
            max_tokens=2500,
            priority=10,
            required_fields=["task"],
            optional_fields=["style_guide", "templates_info"],
            context_type=ContextType.SYSTEM,
        )
        self.context_manager.register_template(template)

    def build_context(
        self,
        task: str,
        document_type: str | None = None,
        style_preferences: dict[str, Any] | None = None,
        template_examples: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        """Build context for Writer Agent.

        Args:
            task: Current writing task
            document_type: Type of document to generate
            style_preferences: Styling preferences
            template_examples: Example templates
            **kwargs: Additional parameters

        Returns:
            Optimized context
        """
        additional_blocks = []

        style_guide = ""
        if style_preferences:
            style_guide = "Style Preferences:\n" + "\n".join(
                f"- {k}: {v}" for k, v in style_preferences.items()
            )

        templates_info = ""
        if template_examples:
            templates_info = "Template Examples:\n" + "\n".join(template_examples[:3])

        if document_type:
            additional_blocks.append(
                ContextBlock(
                    content=f"Document Type: {document_type}",
                    context_type=ContextType.BACKGROUND,
                    priority=8,
                    source="document_type",
                )
            )

        return self.context_manager.build_context(
            template_name="writer_agent",
            additional_context=additional_blocks,
            task=task,
            style_guide=style_guide,
            templates_info=templates_info,
        )


class ValidatorAgentPipeline(ContextPipeline):
    """Context pipeline for Validator Agent."""

    def setup_templates(self) -> None:
        """Setup Validator Agent templates."""
        template = ContextTemplate(
            name="validator_agent",
            description="Context template for validation agent",
            template="""You are a Validation Agent with self-correction capabilities.

**Current Task:** {task}

**Your Responsibilities:**
- Validate documents and outputs
- Check compliance with rules
- Perform quality assurance
- Apply self-correction when errors detected
- Provide confidence scoring

**Validation Layers:**
1. Structural validation (format, required fields)
2. Content validation (accuracy, completeness)
3. Legal compliance (citations, terminology)
4. Quality metrics (readability, clarity)
5. MAGCC consensus evaluation

**Self-Correction Process:**
1. Detect errors or low confidence
2. Analyze root cause
3. Apply corrections
4. Re-validate
5. Update confidence score

**Validation Rules:**
{validation_rules}

**Quality Thresholds:**
- Minimum confidence: 0.8
- Maximum retry attempts: 3
- Required consensus: 0.7""",
            max_tokens=2200,
            priority=10,
            required_fields=["task"],
            optional_fields=["validation_rules"],
            context_type=ContextType.SYSTEM,
        )
        self.context_manager.register_template(template)

    def build_context(
        self,
        task: str,
        validation_rules: list[dict[str, Any]] | None = None,
        previous_validations: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Build context for Validator Agent.

        Args:
            task: Current validation task
            validation_rules: Custom validation rules
            previous_validations: History of validations
            **kwargs: Additional parameters

        Returns:
            Optimized context
        """
        additional_blocks = []

        rules_content = ""
        if validation_rules:
            rules_content = "Custom Validation Rules:\n" + "\n".join(
                f"- {r.get('name', 'Rule')}: {r.get('description', 'N/A')}"
                for r in validation_rules
            )

        if previous_validations:
            history_content = "Previous Validations:\n" + "\n".join(
                f"- {v.get('timestamp', 'N/A')}: Score {v.get('score', 0):.2f}"
                for v in previous_validations[-3:]
            )
            additional_blocks.append(
                ContextBlock(
                    content=history_content,
                    context_type=ContextType.BACKGROUND,
                    priority=6,
                    source="validation_history",
                )
            )

        return self.context_manager.build_context(
            template_name="validator_agent",
            additional_context=additional_blocks,
            task=task,
            validation_rules=rules_content,
        )


class SupervisorAgentPipeline(ContextPipeline):
    """Context pipeline for Supervisor Agent."""

    def setup_templates(self) -> None:
        """Setup Supervisor Agent templates."""
        template = ContextTemplate(
            name="supervisor_agent",
            description="Context template for supervisor/orchestrator agent",
            template="""You are a Supervisor Agent responsible for task orchestration and routing.

**Current Task:** {task}

**Your Responsibilities:**
- Analyze incoming tasks and decompose complex requests
- Route tasks to appropriate specialized agents
- Orchestrate multi-agent workflows
- Monitor execution and handle errors
- Coordinate parallel and sequential operations

**Available Agents:**
{available_agents}

**Routing Strategy:**
1. Analyze task requirements and complexity
2. Identify required capabilities
3. Select appropriate agent(s)
4. Determine execution strategy (sequential/parallel)
5. Monitor progress and handle failures

**Workflow Patterns:**
- Sequential: Task A → Task B → Task C
- Parallel: Task A || Task B || Task C → Merge
- Conditional: If X then Agent A else Agent B
- Loop: Repeat until condition met

**Decision Criteria:**
- Task complexity and scope
- Agent specialization and capabilities
- Resource availability
- Performance requirements
- Error recovery needs""",
            max_tokens=2400,
            priority=10,
            required_fields=["task", "available_agents"],
            context_type=ContextType.SYSTEM,
        )
        self.context_manager.register_template(template)

    def build_context(
        self,
        task: str,
        available_agents: list[str],
        workflow_history: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Build context for Supervisor Agent.

        Args:
            task: Current orchestration task
            available_agents: List of available agent types
            workflow_history: Recent workflow executions
            **kwargs: Additional parameters

        Returns:
            Optimized context
        """
        additional_blocks = []

        agents_content = "\n".join(f"- {agent}" for agent in available_agents)

        if workflow_history:
            history_content = "Recent Workflows:\n" + "\n".join(
                f"- {w.get('workflow_type', 'unknown')}: "
                f"{w.get('status', 'unknown')} ({w.get('duration', 'N/A')}s)"
                for w in workflow_history[-5:]
            )
            additional_blocks.append(
                ContextBlock(
                    content=history_content,
                    context_type=ContextType.BACKGROUND,
                    priority=7,
                    source="workflow_history",
                )
            )

        return self.context_manager.build_context(
            template_name="supervisor_agent",
            additional_context=additional_blocks,
            task=task,
            available_agents=agents_content,
        )


class DefaultPipeline(ContextPipeline):
    """Default context pipeline."""

    def setup_templates(self) -> None:
        """Setup default template."""
        template = ContextTemplate(
            name="default_agent",
            description="Default context template",
            template="""You are an AI Agent assisting with: {task}

**Agent Type:** {agent_type}

**Current Task:** {task}

Please provide helpful, accurate, and professional assistance.

{additional_info}""",
            max_tokens=1500,
            priority=5,
            required_fields=["task", "agent_type"],
            optional_fields=["additional_info"],
            context_type=ContextType.SYSTEM,
        )
        self.context_manager.register_template(template)

    def build_context(self, task: str, agent_type: str = "general", **kwargs: Any) -> str:
        """Build default context.

        Args:
            task: Current task
            agent_type: Type of agent
            **kwargs: Additional parameters

        Returns:
            Optimized context
        """
        return self.context_manager.build_context(
            template_name="default_agent",
            task=task,
            agent_type=agent_type,
            additional_info="",
        )


# Pipeline registry
_PIPELINES: dict[ContextPipelineType, type[ContextPipeline]] = {
    ContextPipelineType.CASE_AGENT: CaseAgentPipeline,
    ContextPipelineType.WRITER_AGENT: WriterAgentPipeline,
    ContextPipelineType.VALIDATOR_AGENT: ValidatorAgentPipeline,
    ContextPipelineType.SUPERVISOR_AGENT: SupervisorAgentPipeline,
    ContextPipelineType.DEFAULT: DefaultPipeline,
}


def create_pipeline(
    pipeline_type: ContextPipelineType, context_manager: ContextManager
) -> ContextPipeline:
    """Create a context pipeline of specified type.

    Args:
        pipeline_type: Type of pipeline to create
        context_manager: ContextManager instance to use

    Returns:
        Initialized context pipeline

    Raises:
        ValueError: If pipeline type not found
    """
    if pipeline_type not in _PIPELINES:
        logger.warning(f"Pipeline type {pipeline_type} not found, using default")
        pipeline_type = ContextPipelineType.DEFAULT

    pipeline_class = _PIPELINES[pipeline_type]
    return pipeline_class(context_manager)
