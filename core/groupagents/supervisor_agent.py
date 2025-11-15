"""Planning-oriented Supervisor Agent for coordinating complex tasks."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
import json
import logging
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field, validator

from ..llm_interface import IntelligentRouter, LLMRequest
from ..memory.memory_manager import MemoryManager
from ..prompts import enhance_prompt_with_cot

logger = logging.getLogger(__name__)

PlanExecutor = Callable[["PlannedSubTask"], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class PlannedSubTask:
    """Single executable unit inside a supervisor plan."""

    id: str
    description: str
    command_type: str
    action: str
    payload: dict[str, Any]
    expected_agent: str | None = None
    requested_tier: str | None = None
    run_mode: Literal["sequential", "parallel"] = "sequential"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "command_type": self.command_type,
            "action": self.action,
            "payload": self.payload,
            "expected_agent": self.expected_agent,
            "requested_tier": self.requested_tier,
            "run_mode": self.run_mode,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class SupervisorPlan:
    """Lightweight container describing the plan generated for a task."""

    steps: list[PlannedSubTask]
    rationale: str

    def as_dict(self) -> list[dict[str, Any]]:
        return [step.to_dict() for step in self.steps]


class SupervisorTaskRequest(BaseModel):
    """Input payload for the supervisor."""

    task: str
    user_id: str
    thread_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    preferred_agents: list[str] = Field(default_factory=list)
    allow_parallel: bool = True
    max_depth: int = Field(default=3, ge=1, le=5)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @validator("task")
    def _ensure_task(cls, value: str) -> str:  # noqa: N805
        if not value.strip():
            raise ValueError("task must not be empty")
        return value


class PlanExecutionResult(BaseModel):
    """Result of executing a single plan step."""

    step_id: str
    description: str
    status: Literal["completed", "failed"]
    output: dict[str, Any] | None = None
    error: str | None = None
    agent: str | None = None


class SupervisorRunResult(BaseModel):
    """Composite result containing the plan and execution trace."""

    plan: list[dict[str, Any]]
    rationale: str
    results: list[PlanExecutionResult]


class SupervisorAgent:
    """LLM-assisted planner capable of orchestrating sub-commands."""

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        *,
        llm_router: IntelligentRouter | None = None,
        max_plan_steps: int = 10,
        use_chain_of_thought: bool = True,
    ) -> None:
        self.memory = memory_manager or MemoryManager()
        self._llm_router = llm_router
        self._max_plan_steps = max_plan_steps
        self.use_cot = use_chain_of_thought

    async def run_task(
        self,
        request: SupervisorTaskRequest,
        executor: PlanExecutor,
    ) -> SupervisorRunResult:
        """Generate a plan for the request and execute it via a callback."""

        if executor is None:
            raise ValueError("SupervisorAgent requires an executor callback")

        plan = await self._build_plan(request)
        results = await self._execute_plan(plan, executor)
        return SupervisorRunResult(
            plan=plan.as_dict(),
            rationale=plan.rationale,
            results=results,
        )

    # ------------------------------------------------------------------ #
    # Planning
    # ------------------------------------------------------------------ #
    async def _build_plan(self, request: SupervisorTaskRequest) -> SupervisorPlan:
        if self._llm_router:
            plan = await self._llm_generate_plan(request)
            if plan:
                return plan
        return self._heuristic_plan(request)

    def _heuristic_plan(self, request: SupervisorTaskRequest) -> SupervisorPlan:
        steps: list[PlannedSubTask] = []
        rationale_parts = ["Heuristic planner activated"]
        task_lower = request.task.lower()
        context = request.context or {}

        steps.append(
            PlannedSubTask(
                id=self._new_step_id(),
                description="Gather context and recent memory",
                command_type="search",
                action="memory_lookup",
                payload={
                    "query": request.task,
                    "context": context,
                },
                expected_agent="rag_pipeline_agent",
            )
        )

        if "case" in task_lower:
            steps.append(
                PlannedSubTask(
                    id=self._new_step_id(),
                    description="Update or retrieve case information",
                    command_type="case",
                    action="update" if "update" in task_lower else "get",
                    payload={
                        "inputs": context.get("case_inputs", {}),
                    },
                    expected_agent="case_agent",
                )
            )
            rationale_parts.append("Detected case-related workflow")

        if any(keyword in task_lower for keyword in ["draft", "document", "petition", "letter"]):
            steps.append(
                PlannedSubTask(
                    id=self._new_step_id(),
                    description="Generate document draft",
                    command_type="generate",
                    action="document",
                    payload={
                        "document_type": context.get("document_type", "petition"),
                        "inputs": context,
                    },
                    expected_agent="writer_agent",
                )
            )
            steps.append(
                PlannedSubTask(
                    id=self._new_step_id(),
                    description="Validate generated content",
                    command_type="validate",
                    action="document",
                    payload={"level": context.get("validation_level", "standard")},
                    expected_agent="validator_agent",
                )
            )
            rationale_parts.append("Document generation flow detected")

        artifacts = context.get("artifacts") or []
        if request.allow_parallel and isinstance(artifacts, Iterable) and len(artifacts) > 1:
            for artifact in artifacts[: self._max_plan_steps]:
                steps.append(
                    PlannedSubTask(
                        id=self._new_step_id(),
                        description=f"Analyze artifact {artifact}",
                        command_type="search",
                        action="artifact_analysis",
                        payload={"artifact": artifact},
                        expected_agent="rag_pipeline_agent",
                        run_mode="parallel",
                    )
                )
            rationale_parts.append("Artifacts analysis scheduled in parallel")

        if not any(step.command_type == "generate" for step in steps):
            steps.append(
                PlannedSubTask(
                    id=self._new_step_id(),
                    description="Provide consolidated answer",
                    command_type="ask",
                    action="summarize",
                    payload={"question": request.task, "context": context},
                    expected_agent="supervisor_agent",
                )
            )

        if len(steps) > self._max_plan_steps:
            steps = steps[: self._max_plan_steps]
            rationale_parts.append("Plan truncated to max steps")

        return SupervisorPlan(steps=steps, rationale=". ".join(rationale_parts))

    async def _llm_generate_plan(self, request: SupervisorTaskRequest) -> SupervisorPlan | None:
        try:
            task_str = request.task
            context_str = json.dumps(request.context, ensure_ascii=False)[:1500]
            constraints_str = ", ".join(request.constraints) or "none"

            prompt = (
                "You are a supervisor planner that must output JSON describing a plan. "
                'Use the schema: {"plan": [{"id": "step-1", "description": str, '
                '"command_type": str, "action": str, "payload": dict, '
                '"expected_agent": str|null, "run_mode": "sequential|parallel"}], '
                '"rationale": str}.\n'
                f"Task: {task_str}\nContext: {context_str}\nConstraints: {constraints_str}\n"
            )

            # Apply Chain-of-Thought enhancement for better planning
            if self.use_cot:
                # Use STRUCTURED template for multi-step planning tasks
                prompt = enhance_prompt_with_cot(prompt, command_type="workflow", action="plan")

            response = await self._llm_router.acomplete(
                LLMRequest(
                    prompt=prompt,
                    temperature=0.2,
                    task_complexity="planning",
                    metadata={"mode": "supervisor_plan"},
                )
            )
            text = response.get("response") or response.get("text") or ""
            data = self._extract_json(text)
            if not data or "plan" not in data:
                return None

            steps: list[PlannedSubTask] = []
            for raw in data["plan"]:
                steps.append(
                    PlannedSubTask(
                        id=raw.get("id") or self._new_step_id(),
                        description=raw.get("description", "Execute task"),
                        command_type=raw.get("command_type", "ask"),
                        action=raw.get("action", "execute"),
                        payload=raw.get("payload") or {},
                        expected_agent=raw.get("expected_agent"),
                        run_mode=raw.get("run_mode", "sequential"),
                        metadata={"llm_origin": True},
                    )
                )

            if not steps:
                return None
            if len(steps) > self._max_plan_steps:
                steps = steps[: self._max_plan_steps]

            rationale = data.get("rationale", "LLM generated plan")
            return SupervisorPlan(steps=steps, rationale=rationale)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("LLM plan generation failed: %s", exc)
            return None

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #
    async def _execute_plan(
        self, plan: SupervisorPlan, executor: PlanExecutor
    ) -> list[PlanExecutionResult]:
        results: list[PlanExecutionResult] = []
        parallel_buffer: list[PlannedSubTask] = []

        async def flush_parallel_buffer() -> None:
            nonlocal parallel_buffer, results
            if not parallel_buffer:
                return
            block = list(parallel_buffer)
            parallel_buffer.clear()
            block_results = await self._execute_parallel_block(block, executor)
            results.extend(block_results)

        for step in plan.steps:
            if step.run_mode == "parallel":
                parallel_buffer.append(step)
                continue
            if parallel_buffer:
                await flush_parallel_buffer()
            results.append(await self._execute_single_step(step, executor))

        if parallel_buffer:
            await flush_parallel_buffer()

        return results

    async def _execute_single_step(
        self, step: PlannedSubTask, executor: PlanExecutor
    ) -> PlanExecutionResult:
        try:
            output = await executor(step)
            return PlanExecutionResult(
                step_id=step.id,
                description=step.description,
                status="completed",
                output=output,
                agent=step.expected_agent,
            )
        except Exception as exc:  # pragma: no cover - executor failure
            logger.exception("Supervisor step failed: %s", exc)
            return PlanExecutionResult(
                step_id=step.id,
                description=step.description,
                status="failed",
                error=str(exc),
                agent=step.expected_agent,
            )

    async def _execute_parallel_block(
        self,
        steps: Iterable[PlannedSubTask],
        executor: PlanExecutor,
    ) -> list[PlanExecutionResult]:
        coros = [self._execute_single_step(step, executor) for step in steps]
        # gather already handles exceptions since _execute_single_step never propagates
        return await asyncio.gather(*coros)

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #
    def _new_step_id(self) -> str:
        return f"step-{uuid.uuid4().hex[:8]}"

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        snippet = text[start : end + 1]
        try:
            data = json.loads(snippet)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return None
        return None
