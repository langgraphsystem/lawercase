from __future__ import annotations

import os
from typing import Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore


class GeminiClient:
    """Google Gemini client with support for latest models (2025).

    Supported Models:
    - gemini-2.5-pro: Most powerful model with 1M context, complex reasoning
    - gemini-2.5-flash: Best price-performance, 1M context, fast
    - gemini-2.5-flash-lite: Cost-efficient, high throughput
    - gemini-2.0-flash: Next-gen features, native tool use, 1M context

    API Parameters:
    - temperature (float, 0.0-2.0): Randomness (default 1.0)
    - max_output_tokens (int): Maximum tokens to generate
    - top_p (float, 0.0-1.0): Nucleus sampling
    - top_k (int): Top-K sampling (default 40)
    - stop_sequences (list[str]): Sequences that stop generation

    Multimodal Support:
    - Text, images, video, audio, PDF inputs (varies by model)
    """

    # Latest model identifiers (2025)
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"

    def __init__(
        self,
        model: str = GEMINI_2_5_PRO,
        api_key: str | None = None,
        temperature: float = 1.0,
        max_output_tokens: int = 8192,
        top_p: float = 0.95,
        top_k: int = 40,
        **kwargs: Any,
    ) -> None:
        """Initialize Gemini client.

        Args:
            model: Model identifier (default: gemini-2.5-pro)
            api_key: Google API key (or set GOOGLE_API_KEY/GEMINI_API_KEY env var)
            temperature: Randomness (0.0-2.0, default 1.0)
            max_output_tokens: Max tokens to generate (default 8192)
            top_p: Nucleus sampling (0.0-1.0, default 0.95)
            top_k: Top-K sampling (default 40)
            **kwargs: Additional parameters
        """
        if genai is None:
            raise ImportError(
                "google-generativeai package not installed. Install with: pip install google-generativeai>=0.8.0"
            )

        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_p = top_p
        self.top_k = top_k
        self.kwargs = kwargs

        # Try multiple environment variable names
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY or GOOGLE_API_KEY env var, or pass api_key parameter."
            )

        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

    async def acomplete(self, prompt: str, **params: Any) -> dict[str, Any]:
        """Async completion using Google Gemini Generative AI API.

        Args:
            prompt: User prompt/message
            **params: Override default parameters

        Returns:
            dict with keys: model, prompt, output, provider, usage, finish_reason
        """
        # Merge default params with overrides
        temperature = params.get("temperature", self.temperature)
        max_output_tokens = params.get("max_output_tokens", self.max_output_tokens)
        top_p = params.get("top_p", self.top_p)
        top_k = params.get("top_k", self.top_k)
        stop_sequences = params.get("stop_sequences", self.kwargs.get("stop_sequences"))

        # Build generation config
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "top_p": top_p,
            "top_k": top_k,
        }

        if stop_sequences:
            generation_config["stop_sequences"] = stop_sequences

        # Call Gemini API
        try:
            # Note: google-generativeai doesn't have async methods by default
            # We'll use sync call (can wrap with asyncio.to_thread if needed)
            response = self.client.generate_content(prompt, generation_config=generation_config)

            # Extract output text
            output_text = response.text if response.text else ""

            # Extract usage metadata (if available)
            usage_metadata = {}
            if hasattr(response, "usage_metadata"):
                usage_metadata = {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    ),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }

            # Extract finish reason
            finish_reason = "unknown"
            if response.candidates and len(response.candidates) > 0:
                finish_reason = str(response.candidates[0].finish_reason)

            return {
                "model": self.model,
                "prompt": prompt,
                "output": output_text,
                "provider": "gemini",
                "usage": usage_metadata,
                "finish_reason": finish_reason,
            }

        except Exception as e:
            return {
                "model": self.model,
                "prompt": prompt,
                "output": f"Error: {e!s}",
                "provider": "gemini",
                "error": str(e),
            }
