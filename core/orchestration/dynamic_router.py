"""Dynamic Agent Router.

LLM-driven routing for task distribution:
- Intelligent agent selection
- Task complexity analysis
- Load balancing
- Fallback strategies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class AgentCapability(str, Enum):
    """Capabilities that agents can have."""

    RESEARCH = "research"
    WRITING = "writing"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    INTAKE = "intake"
    FEEDBACK = "feedback"
    RAG = "rag"
    CASE_MANAGEMENT = "case_management"
    DOCUMENT_GENERATION = "document_generation"
    LEGAL_ANALYSIS = "legal_analysis"


class RoutingStrategy(str, Enum):
    """Strategies for routing tasks."""

    LLM_BASED = "llm_based"  # LLM decides routing
    RULE_BASED = "rule_based"  # Keyword/pattern based
    ROUND_ROBIN = "round_robin"  # Even distribution
    LEAST_LOADED = "least_loaded"  # Load-based
    CAPABILITY_MATCH = "capability_match"  # Match capabilities


@dataclass
class AgentProfile:
    """Profile describing an agent's capabilities."""

    name: str
    capabilities: list[AgentCapability]
    description: str = ""
    priority: int = 5  # 1-10, higher = preferred
    max_concurrent: int = 5
    current_load: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        """Check if agent is available."""
        return self.current_load < self.max_concurrent

    @property
    def load_factor(self) -> float:
        """Current load as percentage."""
        return self.current_load / max(1, self.max_concurrent)


@dataclass
class RoutingDecision:
    """Result of routing decision."""

    agent_name: str
    confidence: float
    reasoning: str
    strategy_used: RoutingStrategy
    alternatives: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingRequest:
    """Request for routing decision."""

    task: str
    task_type: str = "general"
    required_capabilities: list[AgentCapability] = field(default_factory=list)
    preferred_agents: list[str] = field(default_factory=list)
    excluded_agents: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    priority: int = 5


class DynamicRouter:
    """LLM-driven dynamic router for agent selection.

    Features:
    - Multiple routing strategies
    - Agent capability matching
    - Load balancing
    - LLM-based intelligent routing

    Usage:
        router = DynamicRouter()

        # Register agents
        router.register_agent(AgentProfile(
            name="writer_agent",
            capabilities=[AgentCapability.WRITING, AgentCapability.DOCUMENT_GENERATION],
        ))

        # Route task
        decision = await router.route(RoutingRequest(
            task="Write a petition letter",
            task_type="document_generation",
        ))

        print(f"Route to: {decision.agent_name}")
    """

    def __init__(
        self,
        default_strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_MATCH,
        enable_llm_routing: bool = True,
    ) -> None:
        self.default_strategy = default_strategy
        self.enable_llm_routing = enable_llm_routing

        self._agents: dict[str, AgentProfile] = {}
        self._routing_history: list[RoutingDecision] = []
        self._round_robin_index = 0

        # LLM router (lazy loaded)
        self._llm_router = None

    def register_agent(self, profile: AgentProfile) -> None:
        """Register an agent with the router."""
        self._agents[profile.name] = profile
        logger.info(
            "dynamic_router.agent_registered",
            name=profile.name,
            capabilities=[c.value for c in profile.capabilities],
        )

    def unregister_agent(self, name: str) -> None:
        """Remove an agent from the router."""
        self._agents.pop(name, None)

    def update_load(self, agent_name: str, delta: int) -> None:
        """Update agent load."""
        if agent_name in self._agents:
            self._agents[agent_name].current_load = max(
                0,
                self._agents[agent_name].current_load + delta,
            )

    def update_stats(
        self,
        agent_name: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Update agent performance stats."""
        if agent_name not in self._agents:
            return

        agent = self._agents[agent_name]
        # Exponential moving average
        alpha = 0.1
        agent.avg_latency_ms = alpha * latency_ms + (1 - alpha) * agent.avg_latency_ms

        if success:
            agent.success_rate = alpha * 1.0 + (1 - alpha) * agent.success_rate
        else:
            agent.success_rate = alpha * 0.0 + (1 - alpha) * agent.success_rate

    async def route(
        self,
        request: RoutingRequest,
        strategy: RoutingStrategy | None = None,
    ) -> RoutingDecision:
        """Route a task to the appropriate agent.

        Args:
            request: Routing request with task details
            strategy: Override default strategy

        Returns:
            RoutingDecision with selected agent
        """
        strategy = strategy or self.default_strategy

        # Get available agents
        available = self._get_available_agents(request)

        if not available:
            # No agents available, return fallback
            return RoutingDecision(
                agent_name="supervisor_agent",  # Default fallback
                confidence=0.3,
                reasoning="No agents available for task",
                strategy_used=strategy,
            )

        # Route based on strategy
        if strategy == RoutingStrategy.LLM_BASED and self.enable_llm_routing:
            decision = await self._route_llm(request, available)
        elif strategy == RoutingStrategy.RULE_BASED:
            decision = self._route_rule_based(request, available)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            decision = self._route_round_robin(available)
        elif strategy == RoutingStrategy.LEAST_LOADED:
            decision = self._route_least_loaded(available)
        else:  # CAPABILITY_MATCH
            decision = self._route_capability_match(request, available)

        # Record decision
        self._routing_history.append(decision)
        if len(self._routing_history) > 1000:
            self._routing_history = self._routing_history[-500:]

        logger.info(
            "dynamic_router.routed",
            task_type=request.task_type,
            agent=decision.agent_name,
            confidence=decision.confidence,
            strategy=decision.strategy_used.value,
        )

        return decision

    def _get_available_agents(self, request: RoutingRequest) -> list[AgentProfile]:
        """Get agents available for the request."""
        available = []

        for name, agent in self._agents.items():
            # Check exclusions
            if name in request.excluded_agents:
                continue

            # Check availability
            if not agent.is_available:
                continue

            # Check required capabilities
            if request.required_capabilities:
                if not all(cap in agent.capabilities for cap in request.required_capabilities):
                    continue

            available.append(agent)

        # Prioritize preferred agents
        if request.preferred_agents:
            available.sort(
                key=lambda a: (
                    a.name not in request.preferred_agents,
                    -a.priority,
                    a.load_factor,
                )
            )
        else:
            available.sort(key=lambda a: (-a.priority, a.load_factor))

        return available

    def _route_capability_match(
        self,
        request: RoutingRequest,
        available: list[AgentProfile],
    ) -> RoutingDecision:
        """Route based on capability matching."""
        # Score agents by capability match
        scores: list[tuple[AgentProfile, float]] = []

        task_lower = request.task.lower()
        task_type_lower = request.task_type.lower()

        for agent in available:
            score = 0.0

            # Capability match
            for cap in agent.capabilities:
                if cap.value in task_type_lower or cap.value in task_lower:
                    score += 0.3

            # Keywords in description
            if agent.description:
                desc_lower = agent.description.lower()
                for word in task_lower.split()[:10]:
                    if word in desc_lower:
                        score += 0.1

            # Priority bonus
            score += agent.priority * 0.05

            # Success rate bonus
            score += agent.success_rate * 0.2

            # Load penalty
            score -= agent.load_factor * 0.1

            scores.append((agent, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        best = scores[0]
        alternatives = [s[0].name for s in scores[1:4]]

        return RoutingDecision(
            agent_name=best[0].name,
            confidence=min(1.0, best[1]),
            reasoning=f"Capability match score: {best[1]:.2f}",
            strategy_used=RoutingStrategy.CAPABILITY_MATCH,
            alternatives=alternatives,
        )

    def _route_rule_based(
        self,
        request: RoutingRequest,
        available: list[AgentProfile],
    ) -> RoutingDecision:
        """Route based on keyword rules."""
        task_lower = request.task.lower()
        task_type_lower = request.task_type.lower()

        # Define rules
        rules = [
            (["write", "draft", "generate", "document", "letter"], "writer_agent"),
            (["validate", "check", "verify", "review"], "validator_agent"),
            (["search", "find", "lookup", "retrieve"], "rag_pipeline_agent"),
            (["analyze", "evaluate", "assess"], "evidence_analyzer"),
            (["intake", "collect", "gather"], "intake_agent"),
            (["feedback", "comment", "improve"], "feedback_agent"),
            (["case", "petition", "application"], "case_agent"),
        ]

        for keywords, agent_name in rules:
            if any(kw in task_lower or kw in task_type_lower for kw in keywords):
                # Check if agent is available
                matching = [a for a in available if a.name == agent_name]
                if matching:
                    return RoutingDecision(
                        agent_name=agent_name,
                        confidence=0.8,
                        reasoning=f"Rule match: {keywords}",
                        strategy_used=RoutingStrategy.RULE_BASED,
                    )

        # Default to first available
        return RoutingDecision(
            agent_name=available[0].name,
            confidence=0.5,
            reasoning="No rule match, using default",
            strategy_used=RoutingStrategy.RULE_BASED,
        )

    def _route_round_robin(
        self,
        available: list[AgentProfile],
    ) -> RoutingDecision:
        """Route using round-robin."""
        agent = available[self._round_robin_index % len(available)]
        self._round_robin_index += 1

        return RoutingDecision(
            agent_name=agent.name,
            confidence=0.6,
            reasoning="Round-robin selection",
            strategy_used=RoutingStrategy.ROUND_ROBIN,
        )

    def _route_least_loaded(
        self,
        available: list[AgentProfile],
    ) -> RoutingDecision:
        """Route to least loaded agent."""
        sorted_agents = sorted(available, key=lambda a: a.load_factor)
        agent = sorted_agents[0]

        return RoutingDecision(
            agent_name=agent.name,
            confidence=0.7,
            reasoning=f"Least loaded: {agent.load_factor:.1%}",
            strategy_used=RoutingStrategy.LEAST_LOADED,
        )

    async def _route_llm(
        self,
        request: RoutingRequest,
        available: list[AgentProfile],
    ) -> RoutingDecision:
        """Route using LLM decision."""
        try:
            if self._llm_router is None:
                from core.llm_interface import TaskRouter

                self._llm_router = TaskRouter()

            # Build prompt
            agent_descriptions = "\n".join(
                f"- {a.name}: {a.description or 'No description'} "
                f"(capabilities: {', '.join(c.value for c in a.capabilities)})"
                for a in available
            )

            prompt = f"""Select the best agent for this task.

Task: {request.task}
Task Type: {request.task_type}
Context: {request.context}

Available Agents:
{agent_descriptions}

Respond with JSON:
{{"agent": "agent_name", "confidence": 0.0-1.0, "reasoning": "why this agent"}}"""

            from core.llm_interface import TaskRequest, TaskType

            response = await self._llm_router.route(
                TaskRequest(
                    prompt=prompt,
                    task_type=TaskType.GENERAL,
                    temperature=0.2,
                    max_tokens=200,
                )
            )

            # Parse response
            import json
            import re

            match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                agent_name = data.get("agent", available[0].name)
                confidence = data.get("confidence", 0.7)
                reasoning = data.get("reasoning", "LLM selected")

                # Validate agent exists
                if agent_name not in [a.name for a in available]:
                    agent_name = available[0].name
                    confidence = 0.5

                return RoutingDecision(
                    agent_name=agent_name,
                    confidence=confidence,
                    reasoning=reasoning,
                    strategy_used=RoutingStrategy.LLM_BASED,
                )

        except Exception as e:
            logger.warning("dynamic_router.llm_failed", error=str(e))

        # Fallback to capability match
        return self._route_capability_match(request, available)

    def get_agent_stats(self) -> dict[str, Any]:
        """Get statistics for all agents."""
        return {
            name: {
                "current_load": agent.current_load,
                "max_concurrent": agent.max_concurrent,
                "load_factor": agent.load_factor,
                "success_rate": agent.success_rate,
                "avg_latency_ms": agent.avg_latency_ms,
                "is_available": agent.is_available,
            }
            for name, agent in self._agents.items()
        }

    def get_routing_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent routing decisions."""
        return [
            {
                "agent": d.agent_name,
                "confidence": d.confidence,
                "strategy": d.strategy_used.value,
                "reasoning": d.reasoning,
            }
            for d in self._routing_history[-limit:]
        ]


# Default agent profiles
DEFAULT_AGENT_PROFILES = [
    AgentProfile(
        name="writer_agent",
        capabilities=[
            AgentCapability.WRITING,
            AgentCapability.DOCUMENT_GENERATION,
        ],
        description="Generates documents, petition letters, and written content",
        priority=7,
    ),
    AgentProfile(
        name="validator_agent",
        capabilities=[
            AgentCapability.VALIDATION,
            AgentCapability.ANALYSIS,
        ],
        description="Validates documents and evidence against requirements",
        priority=6,
    ),
    AgentProfile(
        name="rag_pipeline_agent",
        capabilities=[
            AgentCapability.RAG,
            AgentCapability.RESEARCH,
        ],
        description="Retrieves and processes knowledge base information",
        priority=7,
    ),
    AgentProfile(
        name="evidence_analyzer",
        capabilities=[
            AgentCapability.ANALYSIS,
            AgentCapability.LEGAL_ANALYSIS,
        ],
        description="Analyzes evidence strength and legal requirements",
        priority=8,
    ),
    AgentProfile(
        name="intake_agent",
        capabilities=[
            AgentCapability.INTAKE,
            AgentCapability.CASE_MANAGEMENT,
        ],
        description="Collects and organizes case information",
        priority=6,
    ),
    AgentProfile(
        name="feedback_agent",
        capabilities=[
            AgentCapability.FEEDBACK,
            AgentCapability.ANALYSIS,
        ],
        description="Provides feedback on documents and processes",
        priority=5,
    ),
    AgentProfile(
        name="case_agent",
        capabilities=[
            AgentCapability.CASE_MANAGEMENT,
            AgentCapability.INTAKE,
        ],
        description="Manages case data and workflow",
        priority=7,
    ),
]


def create_default_router() -> DynamicRouter:
    """Create router with default agent profiles."""
    router = DynamicRouter()
    for profile in DEFAULT_AGENT_PROFILES:
        router.register_agent(profile)
    return router
