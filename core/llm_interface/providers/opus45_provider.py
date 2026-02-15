"""Anthropic Claude Opus 4.5 Provider for legal analysis and complex reasoning.

Claude Opus 4.5 (November 2025):
- claude-opus-4.5: Industry-leading reasoning, coding, and agentic tasks
- 200K context window (1M in beta)

Strengths:
- Legal analysis and interpretation
- Complex reasoning and logic
- Code generation and review
- Data extraction and structured output
- Agentic task execution
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import logging
import os
from typing import Any

from .base_provider import (
    BaseLLMProvider,
    CompletionRequest,
    CompletionResponse,
    ProviderAuthenticationError,
    ProviderContentFilterError,
    ProviderError,
    ProviderModelNotFoundError,
    ProviderQuotaExceededError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderType,
    StreamChunk,
    StreamEvent,
    TokenUsage,
)

logger = logging.getLogger(__name__)

# Try to import Anthropic
try:
    from anthropic import APITimeoutError, AsyncAnthropic, AuthenticationError, RateLimitError

    ANTHROPIC_AVAILABLE = True
except ImportError:
    AsyncAnthropic = None  # type: ignore
    APITimeoutError = None  # type: ignore
    RateLimitError = None  # type: ignore
    AuthenticationError = None  # type: ignore
    ANTHROPIC_AVAILABLE = False


class Opus45Provider(BaseLLMProvider):
    """Anthropic Claude Opus 4.5 provider for legal analysis and complex reasoning.

    Optimized for:
    - Legal analysis and interpretation
    - Complex multi-step reasoning
    - Code generation and review
    - Data extraction
    - Agentic task execution

    Model IDs:
    - claude-opus-4.5: Full capability model (latest)
    - claude-opus-4-5-20251101: Specific version

    Example:
        provider = Opus45Provider(
            api_key="your-api-key",
            model_id="claude-opus-4.5",
        )

        response = await provider.complete(CompletionRequest(
            prompt="Analyze this legal contract for potential issues...",
            max_tokens=4000,
        ))
    """

    # Provider identification
    provider_type = ProviderType.ANTHROPIC
    model_id = "claude-opus-4.5"

    # Available models
    CLAUDE_OPUS_4_5 = "claude-opus-4.5"
    CLAUDE_OPUS_4_5_20251101 = "claude-opus-4-5-20251101"
    CLAUDE_SONNET_4_5 = "claude-sonnet-4.5"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4.5"

    # Model ID mapping (aliases to actual API IDs)
    MODEL_ALIASES = {
        "claude-opus-4.5": "claude-opus-4-5-20251101",
        "claude-sonnet-4.5": "claude-sonnet-4-5-20250929",
        "claude-haiku-4.5": "claude-haiku-4-5-20251001",
    }

    # Pricing (per 1K tokens) - January 2026
    PRICING = {
        "claude-opus-4.5": {"input": 0.015, "output": 0.075},
        "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075},
        "claude-sonnet-4.5": {"input": 0.003, "output": 0.015},
        "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
        "claude-haiku-4.5": {"input": 0.001, "output": 0.005},
        "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
    }

    # Default pricing (Opus 4.5)
    cost_per_1k_input = 0.015
    cost_per_1k_output = 0.075

    # Limits
    max_context_tokens = 200000
    max_output_tokens = 64000

    # Rate limits (default)
    requests_per_minute = 60
    tokens_per_minute = 100000

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str | None = None,
        requests_per_minute: int | None = None,
        tokens_per_minute: int | None = None,
        timeout: float = 180.0,
        base_url: str | None = None,
        enable_extended_thinking: bool = False,
        **kwargs: Any,
    ):
        """Initialize Opus 4.5 provider.

        Args:
            api_key: Anthropic API key (or ANTHROPIC_API_KEY env var)
            model_id: Model identifier (default: claude-opus-4.5)
            requests_per_minute: Override default request rate limit
            tokens_per_minute: Override default token rate limit
            timeout: Request timeout in seconds (longer for complex reasoning)
            base_url: Custom API base URL
            enable_extended_thinking: Enable extended thinking (Claude 4.5 feature)
            **kwargs: Additional options
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. " "Install with: pip install anthropic>=0.40.0"
            )

        # Resolve API key
        resolved_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_api_key:
            raise ProviderAuthenticationError(
                message="Anthropic API key required. Set ANTHROPIC_API_KEY env var.",
                provider=ProviderType.ANTHROPIC,
            )

        # Resolve model ID (handle aliases)
        resolved_model = model_id or self.CLAUDE_OPUS_4_5
        self._api_model_id = self.MODEL_ALIASES.get(resolved_model, resolved_model)

        # Set model-specific pricing
        pricing_key = resolved_model if resolved_model in self.PRICING else self._api_model_id
        if pricing_key in self.PRICING:
            self.cost_per_1k_input = self.PRICING[pricing_key]["input"]
            self.cost_per_1k_output = self.PRICING[pricing_key]["output"]

        self.base_url = base_url
        self.enable_extended_thinking = enable_extended_thinking

        super().__init__(
            api_key=resolved_api_key,
            model_id=resolved_model,
            requests_per_minute=requests_per_minute,
            tokens_per_minute=tokens_per_minute,
            timeout=timeout,
            **kwargs,
        )

    def _initialize_client(self) -> None:
        """Initialize the Anthropic client."""
        client_kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self._client = AsyncAnthropic(**client_kwargs)

        logger.info(
            "Opus 4.5 provider initialized",
            extra={
                "model": self.model_id,
                "api_model": self._api_model_id,
                "extended_thinking": self.enable_extended_thinking,
            },
        )

    def _handle_error(self, error: Exception) -> None:
        """Convert Anthropic errors to provider errors.

        Args:
            error: Original exception

        Raises:
            ProviderError: Converted provider error
        """
        error_str = str(error).lower()

        if AuthenticationError and isinstance(error, AuthenticationError):
            raise ProviderAuthenticationError(
                message=f"Anthropic authentication failed: {error}",
                provider=ProviderType.ANTHROPIC,
                model=self.model_id,
            ) from error

        if RateLimitError and isinstance(error, RateLimitError):
            retry_after = None
            if hasattr(error, "response"):
                headers = getattr(error.response, "headers", {})
                retry_after_str = headers.get("retry-after")
                if retry_after_str:
                    try:
                        retry_after = float(retry_after_str)
                    except ValueError:
                        pass
            raise ProviderRateLimitError(
                message=f"Anthropic rate limit exceeded: {error}",
                provider=ProviderType.ANTHROPIC,
                model=self.model_id,
                retry_after=retry_after,
            ) from error

        if APITimeoutError and isinstance(error, APITimeoutError):
            raise ProviderTimeoutError(
                message=f"Anthropic request timed out: {error}",
                provider=ProviderType.ANTHROPIC,
                model=self.model_id,
                timeout=self.timeout,
            ) from error

        if isinstance(error, TimeoutError | asyncio.TimeoutError):
            raise ProviderTimeoutError(
                message=f"Anthropic request timed out: {error}",
                provider=ProviderType.ANTHROPIC,
                model=self.model_id,
                timeout=self.timeout,
            ) from error

        if "not found" in error_str or "404" in error_str or "model" in error_str:
            raise ProviderModelNotFoundError(
                message=f"Anthropic model not found: {error}",
                provider=ProviderType.ANTHROPIC,
                model=self.model_id,
            ) from error

        if "content" in error_str and ("blocked" in error_str or "filtered" in error_str):
            raise ProviderContentFilterError(
                message=f"Anthropic content filtered: {error}",
                provider=ProviderType.ANTHROPIC,
                filter_reason=str(error),
            ) from error

        if "quota" in error_str or "billing" in error_str or "credit" in error_str:
            raise ProviderQuotaExceededError(
                message=f"Anthropic quota exceeded: {error}",
                provider=ProviderType.ANTHROPIC,
            ) from error

        # Generic error
        raise ProviderError(
            message=f"Anthropic error: {error}",
            provider=ProviderType.ANTHROPIC,
            model=self.model_id,
            recoverable=True,
        ) from error

    async def _complete_impl(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Execute completion using Anthropic API.

        Args:
            request: Completion request

        Returns:
            Completion response
        """
        # Build API parameters
        api_params: dict[str, Any] = {
            "model": self._api_model_id,
            "max_tokens": min(request.max_tokens, self.max_output_tokens),
            "messages": [{"role": "user", "content": request.prompt}],
        }

        # Temperature: use top_p OR temperature, not both
        if request.top_p is not None:
            api_params["top_p"] = request.top_p
        else:
            api_params["temperature"] = request.temperature

        if request.top_k is not None:
            api_params["top_k"] = request.top_k
        if request.stop_sequences:
            api_params["stop_sequences"] = request.stop_sequences
        if request.system_prompt:
            api_params["system"] = request.system_prompt

        try:
            response = await self._client.messages.create(**api_params)

            # Extract content
            output_text = ""
            if response.content and len(response.content) > 0:
                for block in response.content:
                    if hasattr(block, "text"):
                        output_text += block.text

            # Extract usage
            usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            # Extract finish reason
            finish_reason = response.stop_reason or "stop"

            # Calculate cost
            cost = self.calculate_cost(usage)

            return CompletionResponse(
                content=output_text,
                model=self.model_id,
                provider=ProviderType.ANTHROPIC,
                usage=usage,
                cost=cost,
                finish_reason=finish_reason,
                metadata={"response_id": response.id},
            )

        except Exception as e:
            self._handle_error(e)
            raise

    async def _stream_impl(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[StreamChunk]:
        """Execute streaming completion using Anthropic API.

        Args:
            request: Completion request

        Yields:
            Stream chunks
        """
        # Build API parameters
        api_params: dict[str, Any] = {
            "model": self._api_model_id,
            "max_tokens": min(request.max_tokens, self.max_output_tokens),
            "messages": [{"role": "user", "content": request.prompt}],
        }

        # Temperature: use top_p OR temperature, not both
        if request.top_p is not None:
            api_params["top_p"] = request.top_p
        else:
            api_params["temperature"] = request.temperature

        if request.top_k is not None:
            api_params["top_k"] = request.top_k
        if request.stop_sequences:
            api_params["stop_sequences"] = request.stop_sequences
        if request.system_prompt:
            api_params["system"] = request.system_prompt

        try:
            accumulated_text = ""
            input_tokens = 0
            output_tokens = 0

            async with self._client.messages.stream(**api_params) as stream:
                async for event in stream:
                    event_type = getattr(event, "type", "")

                    if event_type == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        if delta and hasattr(delta, "text"):
                            text_delta = delta.text
                            accumulated_text += text_delta
                            yield StreamChunk(
                                event=StreamEvent.TEXT_DELTA,
                                content=accumulated_text,
                                delta=text_delta,
                            )

                    elif event_type == "message_start":
                        message = getattr(event, "message", None)
                        if message and hasattr(message, "usage"):
                            input_tokens = message.usage.input_tokens

                    elif event_type == "message_delta":
                        delta_usage = getattr(event, "usage", None)
                        if delta_usage:
                            output_tokens = delta_usage.output_tokens

            # Emit final usage
            if input_tokens > 0 or output_tokens > 0:
                final_usage = TokenUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                )
                yield StreamChunk(
                    event=StreamEvent.USAGE,
                    content=accumulated_text,
                    usage=final_usage,
                )

            # Emit done
            yield StreamChunk(
                event=StreamEvent.DONE,
                content=accumulated_text,
            )

        except Exception as e:
            yield StreamChunk(
                event=StreamEvent.ERROR,
                content="",
                metadata={"error": str(e)},
            )
            self._handle_error(e)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Note: Anthropic doesn't provide a public tokenizer, so we estimate.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated number of tokens
        """
        # Anthropic uses a similar tokenization to Claude
        # Approximately 1 token per 4 characters for English
        # For more accuracy, consider using the Anthropic token counting API
        return len(text) // 4

    async def analyze_legal_document(
        self,
        document: str,
        analysis_type: str = "comprehensive",
        focus_areas: list[str] | None = None,
        jurisdiction: str | None = None,
        max_tokens: int = 8000,
    ) -> CompletionResponse:
        """Analyze a legal document.

        Optimized for legal analysis tasks.

        Args:
            document: Legal document text
            analysis_type: Type of analysis (comprehensive, risk, compliance, summary)
            focus_areas: Specific areas to focus on
            jurisdiction: Relevant jurisdiction
            max_tokens: Maximum output tokens

        Returns:
            Completion response with legal analysis
        """
        analysis_prompts = {
            "comprehensive": "Provide a comprehensive analysis including key terms, obligations, risks, and recommendations.",
            "risk": "Identify and assess all potential legal risks, liabilities, and problematic clauses.",
            "compliance": "Analyze compliance with relevant regulations and identify any gaps.",
            "summary": "Provide an executive summary of the key provisions and implications.",
        }

        focus_instruction = ""
        if focus_areas:
            focus_instruction = f"\n\nFocus particularly on: {', '.join(focus_areas)}"

        jurisdiction_note = ""
        if jurisdiction:
            jurisdiction_note = (
                f"\n\nConsider the legal requirements and standards of {jurisdiction}."
            )

        prompt = f"""Analyze the following legal document:

<document>
{document}
</document>

{analysis_prompts.get(analysis_type, analysis_prompts['comprehensive'])}{focus_instruction}{jurisdiction_note}

Provide a structured analysis with clear sections and specific citations to relevant document clauses."""

        system_prompt = """You are a senior legal analyst with expertise in contract law, regulatory compliance, and risk assessment.
Provide thorough, precise analysis with specific references to document text.
Always identify key provisions, potential issues, and actionable recommendations."""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for precision
                max_tokens=max_tokens,
            )
        )

    async def complex_reasoning(
        self,
        problem: str,
        context: str | None = None,
        constraints: list[str] | None = None,
        reasoning_style: str = "step_by_step",
        max_tokens: int = 4000,
    ) -> CompletionResponse:
        """Solve complex reasoning problems.

        Args:
            problem: Problem statement
            context: Additional context
            constraints: Constraints to consider
            reasoning_style: Reasoning approach (step_by_step, analytical, comparative)
            max_tokens: Maximum output tokens

        Returns:
            Completion response with reasoning
        """
        style_instructions = {
            "step_by_step": "Think through this step by step, showing your reasoning at each stage.",
            "analytical": "Analyze this systematically, breaking it down into components.",
            "comparative": "Consider multiple approaches and compare their merits.",
        }

        prompt_parts = [f"Problem:\n{problem}"]

        if context:
            prompt_parts.append(f"\nContext:\n{context}")

        if constraints:
            prompt_parts.append("\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints))

        prompt_parts.append(
            f"\n{style_instructions.get(reasoning_style, style_instructions['step_by_step'])}"
        )

        return await self.complete(
            CompletionRequest(
                prompt="\n".join(prompt_parts),
                system_prompt="You are an expert problem solver with strong analytical and logical reasoning skills.",
                temperature=0.5,
                max_tokens=max_tokens,
            )
        )

    async def extract_data(
        self,
        document: str,
        schema: dict[str, Any],
        instructions: str | None = None,
        max_tokens: int = 4000,
    ) -> CompletionResponse:
        """Extract structured data from a document.

        Args:
            document: Document to extract data from
            schema: JSON schema describing expected output structure
            instructions: Additional extraction instructions
            max_tokens: Maximum output tokens

        Returns:
            Completion response with extracted data (as JSON string)
        """
        import json

        schema_str = json.dumps(schema, indent=2)

        prompt = f"""Extract structured data from the following document according to the schema.

<document>
{document}
</document>

<schema>
{schema_str}
</schema>
"""
        if instructions:
            prompt += f"\n<instructions>\n{instructions}\n</instructions>\n"

        prompt += """
Output the extracted data as valid JSON that conforms to the schema.
If a field cannot be determined, use null.
Only output the JSON, no explanations."""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                system_prompt="You are a precise data extraction specialist. Extract information accurately according to the provided schema.",
                temperature=0.1,  # Very low for precision
                max_tokens=max_tokens,
            )
        )

    async def generate_code(
        self,
        task: str,
        language: str,
        context: str | None = None,
        style_guide: str | None = None,
        max_tokens: int = 4000,
    ) -> CompletionResponse:
        """Generate code for a given task.

        Args:
            task: Description of what the code should do
            language: Programming language
            context: Additional context (existing code, APIs, etc.)
            style_guide: Coding style preferences
            max_tokens: Maximum output tokens

        Returns:
            Completion response with generated code
        """
        prompt = f"""Write {language} code to accomplish the following task:

{task}
"""
        if context:
            prompt += f"\nContext:\n{context}\n"

        if style_guide:
            prompt += f"\nStyle Guide:\n{style_guide}\n"

        prompt += """
Provide clean, well-documented code with error handling.
Include comments explaining the logic.
If multiple approaches exist, choose the most efficient and maintainable one."""

        system_prompt = f"""You are an expert {language} developer with strong software engineering practices.
Write clean, efficient, and well-documented code.
Follow best practices for error handling, testing, and maintainability."""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=max_tokens,
            )
        )

    async def review_code(
        self,
        code: str,
        language: str,
        focus: list[str] | None = None,
        max_tokens: int = 4000,
    ) -> CompletionResponse:
        """Review code for issues and improvements.

        Args:
            code: Code to review
            language: Programming language
            focus: Areas to focus on (security, performance, style, bugs)
            max_tokens: Maximum output tokens

        Returns:
            Completion response with code review
        """
        focus_areas = focus or ["bugs", "security", "performance", "readability", "best practices"]

        prompt = f"""Review the following {language} code:

```{language}
{code}
```

Focus on: {', '.join(focus_areas)}

Provide:
1. Issues found (severity: critical/major/minor)
2. Security concerns
3. Performance improvements
4. Code style and readability suggestions
5. Specific recommendations with code examples"""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                system_prompt=f"You are a senior {language} developer conducting a thorough code review.",
                temperature=0.3,
                max_tokens=max_tokens,
            )
        )
