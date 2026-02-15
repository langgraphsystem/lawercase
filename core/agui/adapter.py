"""
AG-UI Adapter - Converts MAS workflow execution to AG-UI events.

Wraps the orchestration workflow and emits standard AG-UI events
for real-time streaming to frontend applications.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

import structlog

from .events import AGUIEvent

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class AGUIAdapter:
    """
    Adapter that wraps MAS workflow execution and emits AG-UI events.

    Usage:
        adapter = AGUIAdapter()

        async for event in adapter.run_workflow(case_id, operation, data):
            yield event.to_sse()  # For SSE endpoint
    """

    def __init__(
        self,
        on_validation_required: Callable[[str, dict], asyncio.Future] | None = None,
    ):
        """
        Initialize AG-UI adapter.

        Args:
            on_validation_required: Callback for human-in-the-loop validation.
                Should return a Future that resolves when user approves/rejects.
        """
        self._on_validation_required = on_validation_required
        self._pending_validations: dict[str, asyncio.Future] = {}

    async def run_workflow(
        self,
        case_id: str,
        operation: str,
        data: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[AGUIEvent]:
        """
        Execute workflow and yield AG-UI events.

        Args:
            case_id: Case identifier
            operation: Workflow operation (create_case, generate_documents, etc.)
            data: Input data for the operation
            user_id: User identifier

        Yields:
            AGUIEvent objects for each workflow step
        """
        from ..di import get_container
        from ..orchestration.workflow_graph import WorkflowState

        # Start event
        checkpoint_id = f"{case_id}_{operation}"
        yield AGUIEvent.run_started(
            case_id=case_id, metadata={"operation": operation, "checkpoint_id": checkpoint_id}
        )

        try:
            container = get_container()
            workflow = container.workflow_graph(operation=operation)

            # Initial state
            normalized_operation = (operation or "").strip().lower()
            # Accept frontend-friendly operation names.
            case_operation_map = {
                "create_case": "create",
                "get_case": "get",
                "update_case": "update",
                "delete_case": "delete",
                "search_cases": "search",
                "start_case_workflow": "start_workflow",
            }
            case_operation = case_operation_map.get(normalized_operation, normalized_operation)

            thread_id = f"{case_id}_{normalized_operation or 'run'}"
            initial_state = WorkflowState(
                thread_id=thread_id,
                case_id=case_id,
                case_operation=case_operation,
                case_data=data or {},
                user_id=user_id,
            )

            # Track workflow execution
            current_step = "start"
            current_agent = None

            yield AGUIEvent.step_started(step_name=current_step)

            # Execute workflow with streaming
            last_update: dict[str, Any] = {}
            async for state_update in self._execute_with_streaming(
                workflow, initial_state, thread_id=thread_id
            ):
                last_update = state_update
                # Emit state delta
                yield AGUIEvent.state_delta(state_update)

                # Check for step changes
                new_step = state_update.get("workflow_step")
                if new_step and new_step != current_step:
                    yield AGUIEvent.step_finished(step_name=current_step)
                    current_step = new_step
                    yield AGUIEvent.step_started(step_name=current_step)

                # Check for agent changes
                new_agent = state_update.get("next_agent")
                if new_agent and new_agent != current_agent:
                    if current_agent:
                        yield AGUIEvent.agent_handoff(from_agent=current_agent, to_agent=new_agent)
                    current_agent = new_agent

                # Check for validation required
                if state_update.get("validation_required"):
                    validation_data = state_update.get("validation_results", {})
                    yield AGUIEvent.validation_required(
                        case_id=case_id,
                        validation_type="document",
                        data=validation_data,
                    )

                    # Wait for human approval if callback provided
                    if self._on_validation_required:
                        approval = await self._on_validation_required(case_id, validation_data)
                        yield AGUIEvent.validation_result(
                            case_id=case_id,
                            approved=approval.get("approved", False),
                            feedback=approval.get("feedback"),
                        )

                # Check for document generation
                if state_update.get("document_content"):
                    doc_id = state_update.get("document_id", "unknown")
                    yield AGUIEvent.document_generated(
                        case_id=case_id,
                        document_type=state_update.get("document_operation", "document"),
                        document_id=doc_id,
                    )

                # Check for errors
                if state_update.get("error"):
                    yield AGUIEvent.run_error(error=state_update["error"], case_id=case_id)

            # Final step
            yield AGUIEvent.step_finished(step_name=current_step)

            # Final state snapshot
            final_output = last_update.get("final_output", {})
            yield AGUIEvent.state_snapshot(
                state={"case_id": case_id, "result": final_output, "checkpoint_id": checkpoint_id}
            )

            # Success
            yield AGUIEvent.run_finished(case_id=case_id)

        except Exception as e:
            logger.exception("agui.workflow.error", case_id=case_id, error=str(e))
            yield AGUIEvent.run_error(error=str(e), case_id=case_id)

    @staticmethod
    def _normalize_state(state: Any) -> dict[str, Any]:
        if state is None:
            return {}
        if isinstance(state, dict):
            # LangGraph often yields dicts keyed by node name -> WorkflowState
            if "workflow_step" in state:
                return state
            for value in state.values():
                if hasattr(value, "model_dump"):
                    return value.model_dump()
                if isinstance(value, dict) and "workflow_step" in value:
                    return value
            return state
        if hasattr(state, "model_dump"):
            return state.model_dump()
        try:
            return dict(state)
        except Exception:
            return {"value": str(state)}

    async def _execute_with_streaming(
        self, workflow: Any, initial_state: Any, *, thread_id: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute workflow and yield state updates.

        This wraps the LangGraph workflow execution to emit incremental updates.
        """
        try:
            config = {
                "configurable": {
                    "thread_id": thread_id or getattr(initial_state, "thread_id", None)
                }
            }

            # For LangGraph workflows with streaming support
            if hasattr(workflow, "astream"):
                async for state in workflow.astream(initial_state, config=config):
                    yield self._normalize_state(state)
            else:
                # Fallback: invoke and yield single result
                result = await workflow.ainvoke(initial_state, config=config)
                yield self._normalize_state(result)

        except Exception as e:
            logger.exception("agui.workflow.streaming_error", error=str(e))
            yield {"error": str(e)}

    async def stream_agent_response(
        self, agent_name: str, prompt: str, case_id: str | None = None
    ) -> AsyncIterator[AGUIEvent]:
        """
        Stream individual agent response with AG-UI events.

        Args:
            agent_name: Name of the agent to invoke
            prompt: User prompt
            case_id: Optional case ID

        Yields:
            AG-UI events for the agent response
        """
        from ..di import get_container

        yield AGUIEvent.run_started(case_id=case_id, agent_name=agent_name)

        message_id = None
        try:
            container = get_container()

            # Get agent based on name
            agent = self._get_agent_by_name(container, agent_name)

            if agent is None:
                yield AGUIEvent.run_error(error=f"Unknown agent: {agent_name}")
                return

            # Start message
            msg_event = AGUIEvent.text_message_start(agent_name=agent_name)
            message_id = msg_event.message_id
            yield msg_event

            # Handle MegaAgent specially - it uses handle_command
            if hasattr(agent, "handle_command"):
                from core.groupagents.mega_agent import CommandType, MegaAgentCommand

                command = MegaAgentCommand(
                    user_id="web_user",
                    command_type=CommandType.ASK,
                    action="answer",
                    payload={"query": prompt, "case_id": case_id},
                )
                response = await agent.handle_command(command)

                # Extract text content from MegaAgentResponse
                response_text = ""
                if response.success and response.result:
                    # Prefer llm_response (LLM-generated answer)
                    response_text = response.result.get("llm_response", "")
                    if not response_text:
                        # Fallback: summarize retrieved context
                        retrieved = response.result.get("retrieved", [])
                        if retrieved:
                            response_text = "Найдено в базе знаний:\n" + "\n".join(
                                f"- {r.get('text', '')[:200]}"
                                for r in retrieved[:5]
                                if r.get("text")
                            )
                        else:
                            response_text = "Информация не найдена."
                elif response.error:
                    response_text = f"Ошибка: {response.error}"
                else:
                    response_text = "Ответ получен."

                yield AGUIEvent.text_message_content(content=response_text, message_id=message_id)
            elif hasattr(agent, "astream"):
                # Stream response if agent supports it
                async for chunk in agent.astream(prompt):
                    yield AGUIEvent.text_message_content(content=chunk, message_id=message_id)
            elif hasattr(agent, "ainvoke"):
                # Fallback: single async response
                result = await agent.ainvoke(prompt)
                response_text = result if isinstance(result, str) else str(result)
                yield AGUIEvent.text_message_content(content=response_text, message_id=message_id)
            else:
                yield AGUIEvent.text_message_content(
                    content=f"Agent {agent_name} does not support invocation",
                    message_id=message_id,
                )

            yield AGUIEvent.text_message_end(message_id=message_id)
            yield AGUIEvent.run_finished(case_id=case_id, agent_name=agent_name)

        except Exception as e:
            logger.exception("agui.agent.error", agent_name=agent_name, error=str(e))
            if message_id:
                yield AGUIEvent.text_message_end(message_id=message_id)
            yield AGUIEvent.run_error(error=str(e), agent_name=agent_name)

    def _get_agent_by_name(self, container: Any, agent_name: str) -> Any | None:
        """Get agent instance by name from DI container."""
        # Map frontend agent names to container keys
        agent_keys = {
            "case_agent": "case_agent",
            "writer_agent": "writer_agent",
            "validator_agent": "validator_agent",
            "feedback_agent": "feedback_agent",
            "supervisor": "supervisor_agent",
            "mega_agent": "mega_agent",
        }
        key = agent_keys.get(agent_name, agent_name)
        try:
            return container.get(key)
        except KeyError:
            logger.error("agui.agent.not_found", agent_name=agent_name, key=key)
            return None
        except Exception as e:
            logger.error("agui.agent.get_error", agent_name=agent_name, error=str(e))
            return None

    # Human-in-the-loop support
    def request_validation(self, case_id: str, data: dict[str, Any]) -> asyncio.Future:
        """
        Request human validation and return a Future that resolves on response.

        Args:
            case_id: Case identifier
            data: Data to validate

        Returns:
            Future that resolves with validation result
        """
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        validation_id = f"{case_id}_{len(self._pending_validations)}"
        self._pending_validations[validation_id] = future
        return future

    def submit_validation_result(
        self, validation_id: str, approved: bool, feedback: str | None = None
    ) -> bool:
        """
        Submit human validation result.

        Args:
            validation_id: Validation request ID
            approved: Whether the validation is approved
            feedback: Optional feedback text

        Returns:
            True if validation was pending, False otherwise
        """
        future = self._pending_validations.pop(validation_id, None)
        if future and not future.done():
            future.set_result({"approved": approved, "feedback": feedback})
            return True
        return False


# Singleton instance for shared use
_adapter_instance: AGUIAdapter | None = None


def get_agui_adapter() -> AGUIAdapter:
    """Get or create singleton AG-UI adapter."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = AGUIAdapter()
    return _adapter_instance
