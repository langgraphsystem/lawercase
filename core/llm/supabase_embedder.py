"""Supabase Vector embeddings client.

The Supabase Vector API exposes an OpenAI-compatible interface for embeddings.
This client wraps that endpoint and provides async helpers the rest of the
codebase can rely on without pulling in OpenAI/Voyage-specific dependencies.

Supports multiple URL sources (in priority order):
1. Explicit api_url parameter
2. SUPABASE_VECTOR_URL environment variable
3. Default OpenAI embeddings endpoint (fallback)

API key selection depends on the endpoint:
- For OpenAI endpoint (api.openai.com): prefer OPENAI_API_KEY
- For Supabase endpoint: prefer SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import SecretStr

from ..storage.config import get_storage_config

# Default OpenAI embeddings endpoint
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


class SupabaseEmbedder:
    """Async helper for calling Supabase Vector embeddings."""

    def __init__(
        self,
        *,
        api_url: str | None = None,
        api_key: SecretStr | None = None,
        model: str | None = None,
        dimension: int | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        config = get_storage_config()

        # URL resolution: explicit > SUPABASE_VECTOR_URL > OpenAI default
        url = api_url or config.supabase_vector_url
        if url is None:
            # Fallback to OpenAI embeddings endpoint
            url = OPENAI_EMBEDDINGS_URL

        self.api_url = url.rstrip("/")

        # API key resolution depends on the URL endpoint
        # For OpenAI endpoint: prefer OPENAI_API_KEY
        # For Supabase endpoint: prefer SUPABASE_SERVICE_ROLE_KEY
        is_openai_endpoint = "api.openai.com" in self.api_url
        key = api_key
        if key is None:
            if is_openai_endpoint:
                # For OpenAI endpoint, prefer OPENAI_API_KEY
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key:
                    key = SecretStr(openai_key)
                # Fallback to Supabase key if no OpenAI key
                if key is None:
                    key = config.supabase_service_role_key
            else:
                # For Supabase endpoint, prefer SUPABASE_SERVICE_ROLE_KEY
                key = config.supabase_service_role_key
                if key is None:
                    openai_key = os.getenv("OPENAI_API_KEY")
                    if openai_key:
                        key = SecretStr(openai_key)
        if key is None:
            raise ValueError(
                "API key required. Set one of: SUPABASE_SERVICE_ROLE_KEY or OPENAI_API_KEY"
            )

        self.api_key = key.get_secret_value()
        self.model = model or config.supabase_embedding_model
        self.dimension = dimension or config.embedding_dimension
        self.timeout = timeout_seconds

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for document chunks."""
        if not texts:
            return []
        return await self._create_embeddings({"input": texts, "model": self.model})

    async def aembed_query(self, text: str) -> list[float]:
        """Generate embedding for a single query string."""
        embeddings = await self._create_embeddings({"input": [text], "model": self.model})
        return embeddings[0] if embeddings else [0.0] * self.dimension

    def get_dimension(self) -> int:
        """Return embedding dimensionality."""
        return self.dimension

    async def _create_embeddings(self, payload: dict[str, Any]) -> list[list[float]]:
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }

        # Add dimensions parameter for variable-dimension models (text-embedding-3-*)
        # This allows us to use 2000 dimensions (max for pgvector HNSW index)
        # instead of the default 3072 for text-embedding-3-large
        if "text-embedding-3" in self.model and self.dimension != 3072:
            payload["dimensions"] = self.dimension
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        results = data.get("data") or data.get("embeddings") or []
        embeddings: list[list[float]] = []
        for item in results:
            vector = item.get("embedding") or item.get("vector")
            if vector is None:
                continue
            embeddings.append(vector)
        return embeddings


def create_supabase_embedder(
    *,
    api_url: str | None = None,
    api_key: SecretStr | None = None,
    model: str | None = None,
    dimension: int | None = None,
) -> SupabaseEmbedder:
    """Factory for SupabaseEmbedder with config defaults."""

    return SupabaseEmbedder(
        api_url=api_url,
        api_key=api_key,
        model=model,
        dimension=dimension,
    )


__all__ = ["SupabaseEmbedder", "create_supabase_embedder"]
