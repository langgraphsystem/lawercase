from __future__ import annotations

"""Task complexity analysis and routing decisions for MegaAgent."""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..llm_interface import IntelligentRouter, LLMRequest

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from core.groupagents.mega_agent import MegaAgentCommand

logger = logging.getLogger(__name__)


class TaskTier(str, Enum):
    """Target execution tier according to the 3-layer architecture."""

    LANGCHAIN = "langchain"  # Tier A – quick tools
    LANGGRAPH = "langgraph"  # Tier B – workflow graph
    DEEP = "deep_agent"  # Tier C – Deep Agents / planners


@dataclass(slots=True)
class ComplexityResult:
    """Normalized routing decision returned by the analyzer."""

    tier: TaskTier
    score: float
    reasons: list[str] = field(default_factory=list)
    recommended_agent: str | None = None
    requires_supervisor: bool = False
    estimated_steps: int = 1
    estimated_cost: float = 0.0


class ComplexityAnalyzer:
    """Estimate task difficulty and recommend the proper execution tier."""

    def __init__(
        self,
        llm_router: IntelligentRouter | None = None,
        *,
        enable_llm: bool = True,
    ) -> None:
        self._llm_router = llm_router
        self._enable_llm = enable_llm

    async def analyze(self, command: MegaAgentCommand) -> ComplexityResult:
        """Return a routing recommendation for the supplied command."""

        score, reasons, agent_hint = self._heuristic_score(command)
        tier = self._tier_from_score(score)
        result = ComplexityResult(
            tier=tier,
            score=score,
            reasons=reasons,
            recommended_agent=agent_hint,
            requires_supervisor=tier is TaskTier.DEEP,
            estimated_steps=self._estimate_steps(tier, command),
            estimated_cost=round(score * 12, 2),
        )

        if (
            self._llm_router
            and self._enable_llm
            and command.payload.get("enable_llm_routing", True)
        ):
            refined = await self._refine_with_llm(command, result)
            if refined:
                result = refined

        return result

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _heuristic_score(self, command: MegaAgentCommand) -> tuple[float, list[str], str | None]:
        action = (command.action or "").lower()
        payload = command.payload or {}
        command_type = str(getattr(command.command_type, "value", command.command_type)).lower()
        base_mapping = {
            "ask": 0.2,
            "search": 0.3,
            "tool": 0.35,
            "case": 0.55,
            "generate": 0.65,
            "validate": 0.6,
            "workflow": 0.75,
            "eb1": 0.85,
            "admin": 0.7,
        }
        score = base_mapping.get(command_type, 0.4)
        reasons = [f"Base score for {command_type}: {score:.2f}"]
        agent_hint = None

        # Payload size / richness
        payload_size = len(payload)
        if payload_size > 3:
            delta = min(0.1, payload_size * 0.02)
            score += delta
            reasons.append(f"Payload has {payload_size} fields (+{delta:.2f})")

        # Attachments or document counts indicate heavier workflows
        documents = payload.get("documents") or payload.get("files") or []
        if isinstance(documents, list) and documents:
            delta = min(0.2, len(documents) * 0.03)
            score += delta
            reasons.append(f"{len(documents)} documents attached (+{delta:.2f})")

        # Explicit markers
        if payload.get("requires_human_review") or payload.get("human_checkpoint"):
            score += 0.1
            reasons.append("Requires human review (+0.10)")

        if payload.get("allow_parallel"):
            score += 0.05
            reasons.append("Parallel execution requested (+0.05)")

        if action in {"full_petition", "comprehensive_review"}:
            score += 0.15
            reasons.append(f"Action '{action}' flagged as deep (+0.15)")

        # Priorities influence complexity
        priority = getattr(command, "priority", 5) or 5
        if priority <= 2:
            score += 0.05
            reasons.append("High priority command (+0.05)")

        agent_hint = payload.get("target_agent") or ("eb1_agent" if command_type == "eb1" else None)

        return min(score, 0.99), reasons, agent_hint

    def _tier_from_score(self, score: float) -> TaskTier:
        if score >= 0.75:
            return TaskTier.DEEP
        if score >= 0.4:
            return TaskTier.LANGGRAPH
        return TaskTier.LANGCHAIN

    def _estimate_steps(self, tier: TaskTier, command: MegaAgentCommand) -> int:
        if tier is TaskTier.DEEP:
            return 6
        if tier is TaskTier.LANGGRAPH:
            return 3
        return 1 if command.command_type.name != "CASE" else 2

    async def _refine_with_llm(
        self, command: MegaAgentCommand, current: ComplexityResult
    ) -> ComplexityResult | None:
        try:
            payload_preview = json.dumps(command.payload, ensure_ascii=False)[:2000]
            prompt = (
                "You are a routing controller for a legal automation system. "
                "Given the command metadata, decide whether it should be executed "
                "by a quick LangChain agent, a LangGraph workflow, or the Deep "
                "Agents planner. Return STRICT JSON with keys: "
                "`tier` (langchain|langgraph|deep_agent), `score` (0-1), "
                "`recommended_agent`, and `reason`.\n\n"
                f"command_type: {command.command_type.name}\n"
                f"action: {command.action}\n"
                f"payload: {payload_preview}\n"
                f"priority: {command.priority}\n"
            )
            request = LLMRequest(
                prompt=prompt,
                temperature=0.0,
                task_complexity="routing",
                metadata={"mode": "complexity_analyzer"},
            )
            response = await self._llm_router.acomplete(request)
            llm_text = response.get("response") or response.get("text") or ""
            data = self._extract_json(llm_text)
            if not data:
                return None

            tier_value = data.get("tier", current.tier.value)
            tier = (
                TaskTier(tier_value) if tier_value in TaskTier._value2member_map_ else current.tier
            )
            score = float(data.get("score", current.score))
            reason = data.get("reason")
            recommended_agent = data.get("recommended_agent") or current.recommended_agent

            reasons = list(current.reasons)
            if reason:
                reasons.append(f"LLM: {reason}")

            return ComplexityResult(
                tier=tier,
                score=max(min(score, 0.99), 0.0),
                reasons=reasons,
                recommended_agent=recommended_agent,
                requires_supervisor=tier is TaskTier.DEEP,
                estimated_steps=self._estimate_steps(tier, command),
                estimated_cost=round(score * 12, 2),
            )
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("LLM routing refinement failed: %s", exc)
            return None

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        """Find the first JSON object in the text and parse it."""
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
