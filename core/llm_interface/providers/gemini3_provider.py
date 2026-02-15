"""Google Gemini 3 Provider for research, analysis, and summarization tasks.

Gemini 3 Models (December 2025):
- gemini-3-pro: State-of-the-art reasoning, 1M context window
- gemini-3-flash: Fast and efficient, best price-performance

Strengths:
- Research and analysis
- Summarization
- Large context processing (up to 1M tokens)
- Multimodal capabilities
- Cost-effective for high-volume tasks
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

# Try to import Google's generative AI library
try:
    import google.generativeai as genai
    from google.generativeai.types import (
        GenerationConfig,
        HarmBlockThreshold,
        HarmCategory,
    )

    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    GenerationConfig = None  # type: ignore
    HarmBlockThreshold = None  # type: ignore
    HarmCategory = None  # type: ignore
    GENAI_AVAILABLE = False


class Gemini3Provider(BaseLLMProvider):
    """Google Gemini 3 provider for research and analysis tasks.

    Optimized for:
    - Research and information gathering
    - Analysis and summarization
    - Large document processing
    - Multimodal understanding

    Model IDs:
    - gemini-3-pro: Full capability model
    - gemini-3-pro-preview: Preview features
    - gemini-3-flash: Fast and efficient

    Example:
        provider = Gemini3Provider(
            api_key="your-api-key",
            model_id="gemini-3-pro",
        )

        response = await provider.complete(CompletionRequest(
            prompt="Summarize the key findings from this research paper...",
            max_tokens=2000,
        ))
    """

    # Provider identification
    provider_type = ProviderType.GEMINI
    model_id = "gemini-3-pro"

    # Available models
    GEMINI_3_PRO = "gemini-3-pro"
    GEMINI_3_PRO_PREVIEW = "gemini-3-pro-preview"
    GEMINI_3_FLASH = "gemini-3-flash"

    # Pricing (per 1K tokens) - January 2026
    PRICING = {
        "gemini-3-pro": {"input": 0.00125, "output": 0.005},
        "gemini-3-pro-preview": {"input": 0.00125, "output": 0.005},
        "gemini-3-flash": {"input": 0.000075, "output": 0.0003},
    }

    # Default pricing
    cost_per_1k_input = 0.00125
    cost_per_1k_output = 0.005

    # Limits
    max_context_tokens = 1000000  # 1M context window
    max_output_tokens = 8192

    # Rate limits (default)
    requests_per_minute = 60
    tokens_per_minute = 1000000

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str | None = None,
        requests_per_minute: int | None = None,
        tokens_per_minute: int | None = None,
        timeout: float = 120.0,
        safety_settings: dict[str, str] | None = None,
        **kwargs: Any,
    ):
        """Initialize Gemini 3 provider.

        Args:
            api_key: Google API key (or GEMINI_API_KEY/GOOGLE_API_KEY env var)
            model_id: Model identifier (default: gemini-3-pro)
            requests_per_minute: Override default request rate limit
            tokens_per_minute: Override default token rate limit
            timeout: Request timeout in seconds
            safety_settings: Custom safety settings
            **kwargs: Additional options
        """
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai>=0.8.0"
            )

        # Resolve API key
        resolved_api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not resolved_api_key:
            raise ProviderAuthenticationError(
                message="Gemini API key required. Set GEMINI_API_KEY or GOOGLE_API_KEY env var.",
                provider=ProviderType.GEMINI,
            )

        # Set model-specific pricing
        resolved_model = model_id or self.GEMINI_3_PRO
        if resolved_model in self.PRICING:
            self.cost_per_1k_input = self.PRICING[resolved_model]["input"]
            self.cost_per_1k_output = self.PRICING[resolved_model]["output"]

        self.safety_settings = safety_settings

        super().__init__(
            api_key=resolved_api_key,
            model_id=resolved_model,
            requests_per_minute=requests_per_minute,
            tokens_per_minute=tokens_per_minute,
            timeout=timeout,
            **kwargs,
        )

    def _initialize_client(self) -> None:
        """Initialize the Gemini client."""
        genai.configure(api_key=self.api_key)

        # Build safety settings
        safety_config = None
        if self.safety_settings:
            safety_config = [
                {
                    "category": getattr(HarmCategory, category.upper()),
                    "threshold": getattr(HarmBlockThreshold, threshold.upper()),
                }
                for category, threshold in self.safety_settings.items()
            ]

        # Create model instance
        self._client = genai.GenerativeModel(
            model_name=self.model_id,
            safety_settings=safety_config,
        )

        logger.info(
            "Gemini 3 provider initialized",
            extra={"model": self.model_id},
        )

    def _build_generation_config(
        self,
        request: CompletionRequest,
    ) -> GenerationConfig:
        """Build generation config from request.

        Args:
            request: Completion request

        Returns:
            GenerationConfig instance
        """
        config_params: dict[str, Any] = {
            "temperature": request.temperature,
            "max_output_tokens": min(request.max_tokens, self.max_output_tokens),
        }

        if request.top_p is not None:
            config_params["top_p"] = request.top_p
        if request.top_k is not None:
            config_params["top_k"] = request.top_k
        if request.stop_sequences:
            config_params["stop_sequences"] = request.stop_sequences

        return GenerationConfig(**config_params)

    def _handle_error(self, error: Exception) -> None:
        """Convert Gemini errors to provider errors.

        Args:
            error: Original exception

        Raises:
            ProviderError: Converted provider error
        """
        error_str = str(error).lower()

        if "api key" in error_str or "authentication" in error_str or "401" in error_str:
            raise ProviderAuthenticationError(
                message=f"Gemini authentication failed: {error}",
                provider=ProviderType.GEMINI,
                model=self.model_id,
            ) from error

        if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
            # Try to extract retry-after
            retry_after = None
            if hasattr(error, "retry_after"):
                retry_after = error.retry_after
            raise ProviderRateLimitError(
                message=f"Gemini rate limit exceeded: {error}",
                provider=ProviderType.GEMINI,
                model=self.model_id,
                retry_after=retry_after,
            ) from error

        if "timeout" in error_str or isinstance(error, TimeoutError | asyncio.TimeoutError):
            raise ProviderTimeoutError(
                message=f"Gemini request timed out: {error}",
                provider=ProviderType.GEMINI,
                model=self.model_id,
                timeout=self.timeout,
            ) from error

        if "not found" in error_str or "404" in error_str:
            raise ProviderModelNotFoundError(
                message=f"Gemini model not found: {error}",
                provider=ProviderType.GEMINI,
                model=self.model_id,
            ) from error

        if "blocked" in error_str or "safety" in error_str or "harmful" in error_str:
            raise ProviderContentFilterError(
                message=f"Gemini content filtered: {error}",
                provider=ProviderType.GEMINI,
                filter_reason=str(error),
            ) from error

        if "quota" in error_str or "billing" in error_str:
            raise ProviderQuotaExceededError(
                message=f"Gemini quota exceeded: {error}",
                provider=ProviderType.GEMINI,
            ) from error

        # Generic error
        raise ProviderError(
            message=f"Gemini error: {error}",
            provider=ProviderType.GEMINI,
            model=self.model_id,
            recoverable=True,
        ) from error

    async def _complete_impl(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Execute completion using Gemini API.

        Args:
            request: Completion request

        Returns:
            Completion response
        """
        generation_config = self._build_generation_config(request)

        # Build prompt with system instruction
        prompt = request.prompt
        if request.system_prompt:
            # Gemini handles system prompts via model configuration
            # For now, prepend to prompt
            prompt = f"System: {request.system_prompt}\n\nUser: {prompt}"

        try:
            # Run in thread since google-generativeai is sync
            response = await asyncio.to_thread(
                self._client.generate_content,
                prompt,
                generation_config=generation_config,
            )

            # Extract text
            output_text = ""
            if response.text:
                output_text = response.text
            elif response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    output_text = "".join(
                        part.text for part in candidate.content.parts if hasattr(part, "text")
                    )

            # Extract usage
            usage = TokenUsage()
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = TokenUsage(
                    input_tokens=getattr(response.usage_metadata, "prompt_token_count", 0),
                    output_tokens=getattr(response.usage_metadata, "candidates_token_count", 0),
                    total_tokens=getattr(response.usage_metadata, "total_token_count", 0),
                )

            # Extract finish reason
            finish_reason = "stop"
            if response.candidates and len(response.candidates) > 0:
                finish_reason = str(response.candidates[0].finish_reason).lower()

            # Calculate cost
            cost = self.calculate_cost(usage)

            return CompletionResponse(
                content=output_text,
                model=self.model_id,
                provider=ProviderType.GEMINI,
                usage=usage,
                cost=cost,
                finish_reason=finish_reason,
                metadata={"response_id": getattr(response, "response_id", None)},
            )

        except Exception as e:
            self._handle_error(e)
            # This line is never reached but satisfies type checker
            raise

    async def _stream_impl(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[StreamChunk]:
        """Execute streaming completion using Gemini API.

        Args:
            request: Completion request

        Yields:
            Stream chunks
        """
        generation_config = self._build_generation_config(request)

        # Build prompt with system instruction
        prompt = request.prompt
        if request.system_prompt:
            prompt = f"System: {request.system_prompt}\n\nUser: {prompt}"

        try:
            # Start streaming in thread
            response_stream = await asyncio.to_thread(
                self._client.generate_content,
                prompt,
                generation_config=generation_config,
                stream=True,
            )

            accumulated_text = ""
            final_usage: TokenUsage | None = None

            # Process stream
            for chunk in response_stream:
                if chunk.text:
                    delta = chunk.text
                    accumulated_text += delta

                    yield StreamChunk(
                        event=StreamEvent.TEXT_DELTA,
                        content=accumulated_text,
                        delta=delta,
                    )

                # Check for usage in final chunk
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    final_usage = TokenUsage(
                        input_tokens=getattr(chunk.usage_metadata, "prompt_token_count", 0),
                        output_tokens=getattr(chunk.usage_metadata, "candidates_token_count", 0),
                        total_tokens=getattr(chunk.usage_metadata, "total_token_count", 0),
                    )

            # Emit final usage if available
            if final_usage:
                yield StreamChunk(
                    event=StreamEvent.USAGE,
                    content=accumulated_text,
                    usage=final_usage,
                )

            # Emit done event
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
        """Count tokens in text using Gemini tokenizer.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            # Use Gemini's count_tokens method
            result = self._client.count_tokens(text)
            return result.total_tokens
        except Exception:
            # Fallback: estimate based on characters
            # Average ~4 characters per token for English
            return len(text) // 4

    async def analyze_document(
        self,
        document_text: str,
        analysis_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> CompletionResponse:
        """Analyze a document using Gemini's large context window.

        Optimized for research and analysis tasks.

        Args:
            document_text: Full document text
            analysis_prompt: What to analyze
            max_tokens: Maximum output tokens
            temperature: Sampling temperature

        Returns:
            Completion response with analysis
        """
        prompt = f"""Analyze the following document:

<document>
{document_text}
</document>

{analysis_prompt}"""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )

    async def summarize(
        self,
        text: str,
        style: str = "concise",
        max_length: int = 500,
        temperature: float = 0.3,
    ) -> CompletionResponse:
        """Summarize text.

        Args:
            text: Text to summarize
            style: Summary style (concise, detailed, bullet_points)
            max_length: Maximum summary length in tokens
            temperature: Sampling temperature

        Returns:
            Completion response with summary
        """
        style_prompts = {
            "concise": "Provide a concise summary that captures the key points.",
            "detailed": "Provide a detailed summary that covers all important aspects.",
            "bullet_points": "Summarize the key points as bullet points.",
        }

        prompt = f"""Summarize the following text. {style_prompts.get(style, style_prompts['concise'])}

<text>
{text}
</text>

Summary:"""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_length,
            )
        )

    async def research(
        self,
        query: str,
        context: str | None = None,
        depth: str = "standard",
        max_tokens: int = 4096,
    ) -> CompletionResponse:
        """Conduct research on a topic.

        Args:
            query: Research query
            context: Additional context
            depth: Research depth (quick, standard, comprehensive)
            max_tokens: Maximum output tokens

        Returns:
            Completion response with research findings
        """
        depth_prompts = {
            "quick": "Provide a quick overview with key facts.",
            "standard": "Provide a thorough analysis with supporting evidence.",
            "comprehensive": "Provide an exhaustive analysis covering all aspects, including edge cases and alternative viewpoints.",
        }

        prompt = f"""Research the following topic:

Query: {query}
"""
        if context:
            prompt += f"""
Context:
{context}
"""
        prompt += f"""
{depth_prompts.get(depth, depth_prompts['standard'])}

Provide your findings with clear organization and citations where applicable."""

        return await self.complete(
            CompletionRequest(
                prompt=prompt,
                temperature=0.5,
                max_tokens=max_tokens,
            )
        )
