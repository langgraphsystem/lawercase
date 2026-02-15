"""Task-based LLM Router for Gemini 3, ChatGPT 5.2, and Opus 4.5.

Routes tasks to the optimal model based on task type:
- Legal Analysis → Opus 4.5
- Document Generation → ChatGPT 5.2
- Research/Analysis → Gemini 3
- Code Generation → Opus 4.5
- Summarization → Gemini 3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
from typing import Any

from .anthropic_client import AnthropicClient
from .fallback_manager import FallbackManager
from .gemini_client import GeminiClient
from .openai_client import OpenAIClient


class TaskType(str, Enum):
    """Supported task types for routing."""

    LEGAL_ANALYSIS = "legal_analysis"
    DOCUMENT_GENERATION = "document_generation"
    RESEARCH = "research"
    CODE_GENERATION = "code_generation"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CONVERSATION = "conversation"
    CREATIVE_WRITING = "creative_writing"
    DATA_EXTRACTION = "data_extraction"
    GENERAL = "general"


class ModelProvider(str, Enum):
    """Available LLM providers."""

    GEMINI_3 = "gemini-3"
    CHATGPT_52 = "chatgpt-5.2"
    OPUS_45 = "opus-4.5"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    provider: ModelProvider
    model_id: str
    strengths: list[TaskType]
    cost_per_1k_input: float  # USD
    cost_per_1k_output: float  # USD
    max_context: int  # tokens
    priority: int = 1  # Lower = higher priority for fallback


# Model configurations
MODEL_CONFIGS: dict[ModelProvider, ModelConfig] = {
    ModelProvider.OPUS_45: ModelConfig(
        provider=ModelProvider.OPUS_45,
        model_id="claude-opus-4-5-20251101",
        strengths=[
            TaskType.LEGAL_ANALYSIS,
            TaskType.CODE_GENERATION,
            TaskType.DATA_EXTRACTION,
        ],
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        max_context=200000,
        priority=1,
    ),
    ModelProvider.CHATGPT_52: ModelConfig(
        provider=ModelProvider.CHATGPT_52,
        model_id="gpt-5.2-turbo",  # Placeholder - update when available
        strengths=[
            TaskType.DOCUMENT_GENERATION,
            TaskType.CREATIVE_WRITING,
            TaskType.CONVERSATION,
            TaskType.TRANSLATION,
        ],
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.03,
        max_context=128000,
        priority=2,
    ),
    ModelProvider.GEMINI_3: ModelConfig(
        provider=ModelProvider.GEMINI_3,
        model_id="gemini-3-pro-preview",
        strengths=[
            TaskType.RESEARCH,
            TaskType.SUMMARIZATION,
            TaskType.GENERAL,
        ],
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.005,
        max_context=1000000,
        priority=3,
    ),
}


# Task to model mapping (primary and fallback)
TASK_ROUTING: dict[TaskType, list[ModelProvider]] = {
    TaskType.LEGAL_ANALYSIS: [
        ModelProvider.OPUS_45,
        ModelProvider.CHATGPT_52,
        ModelProvider.GEMINI_3,
    ],
    TaskType.DOCUMENT_GENERATION: [
        ModelProvider.CHATGPT_52,
        ModelProvider.OPUS_45,
        ModelProvider.GEMINI_3,
    ],
    TaskType.RESEARCH: [
        ModelProvider.GEMINI_3,
        ModelProvider.CHATGPT_52,
        ModelProvider.OPUS_45,
    ],
    TaskType.CODE_GENERATION: [
        ModelProvider.OPUS_45,
        ModelProvider.GEMINI_3,
        ModelProvider.CHATGPT_52,
    ],
    TaskType.SUMMARIZATION: [
        ModelProvider.GEMINI_3,
        ModelProvider.CHATGPT_52,
        ModelProvider.OPUS_45,
    ],
    TaskType.TRANSLATION: [
        ModelProvider.CHATGPT_52,
        ModelProvider.GEMINI_3,
        ModelProvider.OPUS_45,
    ],
    TaskType.CONVERSATION: [
        ModelProvider.CHATGPT_52,
        ModelProvider.OPUS_45,
        ModelProvider.GEMINI_3,
    ],
    TaskType.CREATIVE_WRITING: [
        ModelProvider.CHATGPT_52,
        ModelProvider.OPUS_45,
        ModelProvider.GEMINI_3,
    ],
    TaskType.DATA_EXTRACTION: [
        ModelProvider.OPUS_45,
        ModelProvider.GEMINI_3,
        ModelProvider.CHATGPT_52,
    ],
    TaskType.GENERAL: [
        ModelProvider.GEMINI_3,
        ModelProvider.CHATGPT_52,
        ModelProvider.OPUS_45,
    ],
}


@dataclass(slots=True)
class TaskRequest:
    """Request for task-based LLM routing."""

    prompt: str
    task_type: TaskType = TaskType.GENERAL
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str | None = None
    preferred_provider: ModelProvider | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskResponse:
    """Response from task-based LLM router."""

    content: str
    provider: ModelProvider
    model_id: str
    task_type: TaskType
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    fallback_used: bool = False
    error: str | None = None


class TaskRouter:
    """Task-based LLM router with automatic fallback.

    Routes requests to optimal model based on task type:
    - Legal Analysis → Opus 4.5 (best reasoning)
    - Document Generation → ChatGPT 5.2 (best writing)
    - Research/Analysis → Gemini 3 (largest context, fastest)
    - Code Generation → Opus 4.5 (best coding)

    Features:
    - Automatic fallback on errors
    - Cost tracking
    - Provider health monitoring

    Usage:
        router = TaskRouter()

        # Route by task type
        response = await router.route(TaskRequest(
            prompt="Analyze this legal document...",
            task_type=TaskType.LEGAL_ANALYSIS,
        ))

        # Force specific provider
        response = await router.route(TaskRequest(
            prompt="Write a poem...",
            preferred_provider=ModelProvider.CHATGPT_52,
        ))
    """

    def __init__(
        self,
        anthropic_api_key: str | None = None,
        openai_api_key: str | None = None,
        gemini_api_key: str | None = None,
    ) -> None:
        """Initialize task router with all providers.

        Args:
            anthropic_api_key: Anthropic API key (or ANTHROPIC_API_KEY env)
            openai_api_key: OpenAI API key (or OPENAI_API_KEY env)
            gemini_api_key: Google API key (or GEMINI_API_KEY env)
        """
        self._clients: dict[ModelProvider, Any] = {}
        self._available: dict[ModelProvider, bool] = {}

        # Initialize Anthropic (Opus 4.5)
        try:
            api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self._clients[ModelProvider.OPUS_45] = AnthropicClient(
                    model=MODEL_CONFIGS[ModelProvider.OPUS_45].model_id,
                    api_key=api_key,
                )
                self._available[ModelProvider.OPUS_45] = True
            else:
                self._available[ModelProvider.OPUS_45] = False
        except Exception:
            self._available[ModelProvider.OPUS_45] = False

        # Initialize OpenAI (ChatGPT 5.2)
        try:
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self._clients[ModelProvider.CHATGPT_52] = OpenAIClient(
                    model=MODEL_CONFIGS[ModelProvider.CHATGPT_52].model_id,
                    api_key=api_key,
                )
                self._available[ModelProvider.CHATGPT_52] = True
            else:
                self._available[ModelProvider.CHATGPT_52] = False
        except Exception:
            self._available[ModelProvider.CHATGPT_52] = False

        # Initialize Gemini (Gemini 3)
        try:
            api_key = gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                self._clients[ModelProvider.GEMINI_3] = GeminiClient(
                    model=MODEL_CONFIGS[ModelProvider.GEMINI_3].model_id,
                    api_key=api_key,
                )
                self._available[ModelProvider.GEMINI_3] = True
            else:
                self._available[ModelProvider.GEMINI_3] = False
        except Exception:
            self._available[ModelProvider.GEMINI_3] = False

        # Initialize fallback manager
        self._fallback_manager = FallbackManager()

        # Stats
        self._total_requests = 0
        self._fallback_count = 0
        self._costs: dict[ModelProvider, float] = dict.fromkeys(ModelProvider, 0.0)

    def _select_provider(self, request: TaskRequest) -> list[ModelProvider]:
        """Select provider chain for request."""
        # If preferred provider specified and available
        if request.preferred_provider:
            if self._available.get(request.preferred_provider):
                chain = [request.preferred_provider]
                # Add fallbacks
                for provider in TASK_ROUTING.get(request.task_type, []):
                    if provider != request.preferred_provider and self._available.get(provider):
                        chain.append(provider)
                return chain

        # Use task-based routing
        task_chain = TASK_ROUTING.get(request.task_type, TASK_ROUTING[TaskType.GENERAL])
        return [p for p in task_chain if self._available.get(p)]

    def _calculate_cost(
        self,
        provider: ModelProvider,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for request."""
        config = MODEL_CONFIGS[provider]
        input_cost = (input_tokens / 1000) * config.cost_per_1k_input
        output_cost = (output_tokens / 1000) * config.cost_per_1k_output
        return input_cost + output_cost

    async def route(self, request: TaskRequest) -> TaskResponse:
        """Route request to optimal model with fallback.

        Args:
            request: Task request with prompt and metadata

        Returns:
            TaskResponse with generated content
        """
        import time

        self._total_requests += 1
        start_time = time.perf_counter()

        provider_chain = self._select_provider(request)

        if not provider_chain:
            return TaskResponse(
                content="",
                provider=ModelProvider.GEMINI_3,
                model_id="none",
                task_type=request.task_type,
                error="No LLM providers available. Check API keys.",
            )

        fallback_used = False
        last_error = None

        for i, provider in enumerate(provider_chain):
            if i > 0:
                fallback_used = True
                self._fallback_count += 1

            client = self._clients.get(provider)
            if not client:
                continue

            try:
                # Call the appropriate client
                result = await client.acomplete(
                    prompt=request.prompt,
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                    system=request.system_prompt,
                )

                # Extract response
                content = (
                    result.get("output") or result.get("response") or result.get("content", "")
                )
                usage = result.get("usage", {})
                input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens", 0)
                output_tokens = usage.get("completion_tokens") or usage.get("output_tokens", 0)

                # Calculate cost
                cost = self._calculate_cost(provider, input_tokens, output_tokens)
                self._costs[provider] += cost

                elapsed_ms = (time.perf_counter() - start_time) * 1000

                return TaskResponse(
                    content=content,
                    provider=provider,
                    model_id=MODEL_CONFIGS[provider].model_id,
                    task_type=request.task_type,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    latency_ms=elapsed_ms,
                    fallback_used=fallback_used,
                )

            except Exception as e:
                last_error = str(e)
                # Mark provider as temporarily unavailable
                self._fallback_manager.record_failure(provider.value)
                continue

        # All providers failed
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return TaskResponse(
            content="",
            provider=provider_chain[0] if provider_chain else ModelProvider.GEMINI_3,
            model_id="none",
            task_type=request.task_type,
            latency_ms=elapsed_ms,
            fallback_used=fallback_used,
            error=f"All providers failed. Last error: {last_error}",
        )

    def get_stats(self) -> dict[str, Any]:
        """Get router statistics."""
        return {
            "total_requests": self._total_requests,
            "fallback_count": self._fallback_count,
            "fallback_rate": self._fallback_count / max(1, self._total_requests),
            "available_providers": [p.value for p, avail in self._available.items() if avail],
            "unavailable_providers": [p.value for p, avail in self._available.items() if not avail],
            "total_cost_usd": sum(self._costs.values()),
            "cost_by_provider": {p.value: c for p, c in self._costs.items()},
        }

    def get_recommended_provider(self, task_type: TaskType) -> ModelProvider | None:
        """Get recommended provider for task type."""
        chain = TASK_ROUTING.get(task_type, [])
        for provider in chain:
            if self._available.get(provider):
                return provider
        return None
