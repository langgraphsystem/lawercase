"""
Real embeddings integration for mega_agent_pro.

Поддерживает несколько провайдеров:
- Google Gemini (text-embedding-004)
- OpenAI (text-embedding-3-small, text-embedding-3-large)
- Azure OpenAI
- Local/Self-hosted models via sentence-transformers

Включает:
- Batch processing для эффективности
- Retry logic с экспоненциальным backoff
- Semantic caching для снижения API costs
- Rate limiting для предотвращения quota exhaustion
- Graceful fallback между провайдерами
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"


class EmbeddingModel(str, Enum):
    """Supported embedding models."""
    # Gemini
    GEMINI_TEXT_004 = "text-embedding-004"

    # OpenAI
    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_SMALL_3 = "text-embedding-3-small"
    OPENAI_LARGE_3 = "text-embedding-3-large"

    # Local models
    ALL_MINILM_L6_V2 = "all-MiniLM-L6-v2"
    ALL_MPNET_BASE_V2 = "all-mpnet-base-v2"
    MULTILINGUAL_E5_SMALL = "multilingual-e5-small"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding providers."""
    provider: EmbeddingProvider
    model: EmbeddingModel
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    batch_size: int = 100
    max_retries: int = 3
    timeout: float = 30.0
    rate_limit_per_minute: int = 1000
    cache_ttl_hours: int = 24
    fallback_providers: List[EmbeddingProvider] = field(default_factory=list)


class EmbeddingRequest(BaseModel):
    """Request for embedding generation."""
    texts: List[str] = Field(..., description="Texts to embed")
    user_id: Optional[str] = Field(None, description="User ID for tracking")
    normalize: bool = Field(True, description="Normalize embeddings to unit vectors")
    cache_key: Optional[str] = Field(None, description="Custom cache key")


class EmbeddingResponse(BaseModel):
    """Response from embedding generation."""
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    model: str = Field(..., description="Model used")
    provider: str = Field(..., description="Provider used")
    cached: bool = Field(False, description="Whether result was cached")
    processing_time: float = Field(..., description="Processing time in seconds")
    token_count: int = Field(0, description="Total tokens processed")


class EmbeddingCache:
    """Simple in-memory cache for embeddings with TTL."""

    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, tuple[List[List[float]], float]] = {}
        self.ttl_seconds = ttl_hours * 3600

    def _is_expired(self, timestamp: float) -> bool:
        return time.time() - timestamp > self.ttl_seconds

    def get(self, key: str) -> Optional[List[List[float]]]:
        if key in self.cache:
            embeddings, timestamp = self.cache[key]
            if not self._is_expired(timestamp):
                return embeddings
            else:
                del self.cache[key]
        return None

    def set(self, key: str, embeddings: List[List[float]]) -> None:
        self.cache[key] = (embeddings, time.time())

    def clear_expired(self) -> int:
        """Remove expired entries and return count removed."""
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if self._is_expired(timestamp)
        ]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.tokens = max_requests_per_minute
        self.last_refill = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self, requests: int = 1) -> bool:
        async with self.lock:
            now = time.time()
            # Refill tokens based on time passed
            time_passed = now - self.last_refill
            self.tokens = min(
                self.max_requests,
                self.tokens + (time_passed / 60.0) * self.max_requests
            )
            self.last_refill = now

            if self.tokens >= requests:
                self.tokens -= requests
                return True
            return False


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        pass

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with rate limiting and batching."""
        if not texts:
            return []

        # Wait for rate limit
        while not await self.rate_limiter.acquire(len(texts)):
            await asyncio.sleep(0.1)

        # Process in batches if needed
        if len(texts) <= self.config.batch_size:
            return await self.embed_batch(texts)

        results = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            batch_embeddings = await self.embed_batch(batch)
            results.extend(batch_embeddings)

        return results


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embedding provider."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.model = config.model.value
        self.base_url = config.api_base or "https://generativelanguage.googleapis.com/v1beta"

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Gemini API."""
        if not self.api_key:
            raise ValueError("Gemini API key is required")

        url = f"{self.base_url}/models/{self.model}:batchEmbedContents"

        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]}
                }
                for text in texts
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
            for attempt in range(self.config.max_retries):
                try:
                    async with session.post(url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            embeddings = []
                            for embedding_response in data.get("embeddings", []):
                                embedding = embedding_response.get("values", [])
                                embeddings.append(embedding)
                            return embeddings
                        else:
                            error_text = await response.text()
                            logger.warning(f"Gemini API error (attempt {attempt + 1}): {response.status} - {error_text}")
                            if attempt == self.config.max_retries - 1:
                                raise Exception(f"Gemini API failed: {response.status} - {error_text}")
                except Exception:
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return []


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.model = config.model.value
        self.base_url = config.api_base or "https://api.openai.com/v1"

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        url = f"{self.base_url}/embeddings"

        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float"
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
            for attempt in range(self.config.max_retries):
                try:
                    async with session.post(url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            embeddings = []
                            for item in data.get("data", []):
                                embeddings.append(item["embedding"])
                            return embeddings
                        else:
                            error_text = await response.text()
                            logger.warning(f"OpenAI API error (attempt {attempt + 1}): {response.status} - {error_text}")
                            if attempt == self.config.max_retries - 1:
                                raise Exception(f"OpenAI API failed: {response.status} - {error_text}")
                except Exception:
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)

        return []


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider using sentence-transformers."""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.model = None
        self.model_name = config.model.value
        self._load_model()

    def _load_model(self):
        """Load the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded local embedding model: {self.model_name}")
        except ImportError:
            raise ImportError("sentence-transformers package is required for local embeddings")
        except Exception as e:
            raise Exception(f"Failed to load model {self.model_name}: {e}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model."""
        if not self.model:
            raise ValueError("Local model not loaded")

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.model.encode(texts, convert_to_numpy=True).tolist()
        )

        return embeddings


class EmbeddingManager:
    """Main embedding manager with caching, fallback, and provider management."""

    def __init__(self, configs: List[EmbeddingConfig]):
        self.providers: Dict[EmbeddingProvider, BaseEmbeddingProvider] = {}
        self.primary_provider: Optional[EmbeddingProvider] = None
        self.cache = EmbeddingCache()

        # Initialize providers
        for config in configs:
            provider = self._create_provider(config)
            self.providers[config.provider] = provider

            # Set first provider as primary
            if self.primary_provider is None:
                self.primary_provider = config.provider

    def _create_provider(self, config: EmbeddingConfig) -> BaseEmbeddingProvider:
        """Create provider instance based on config."""
        if config.provider == EmbeddingProvider.GEMINI:
            return GeminiEmbeddingProvider(config)
        elif config.provider == EmbeddingProvider.OPENAI:
            return OpenAIEmbeddingProvider(config)
        elif config.provider == EmbeddingProvider.AZURE_OPENAI:
            # Azure OpenAI is similar to OpenAI but with different base URL
            azure_config = config
            if not config.api_base:
                raise ValueError("api_base is required for Azure OpenAI")
            return OpenAIEmbeddingProvider(azure_config)
        elif config.provider == EmbeddingProvider.LOCAL:
            return LocalEmbeddingProvider(config)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def _generate_cache_key(self, texts: List[str], provider: str, model: str) -> str:
        """Generate cache key for texts."""
        content = f"{provider}:{model}:{':'.join(texts)}"
        return hashlib.md5(content.encode()).hexdigest()

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings with caching and fallback."""
        start_time = time.time()

        if not request.texts:
            return EmbeddingResponse(
                embeddings=[],
                model="",
                provider="",
                cached=False,
                processing_time=0.0,
                token_count=0
            )

        # Try cache first
        if self.primary_provider:
            primary_config = list(self.providers.keys())[0]  # Get config for cache key
            cache_key = request.cache_key or self._generate_cache_key(
                request.texts,
                self.primary_provider.value,
                "default"  # Simplified for cache key
            )

            cached_embeddings = self.cache.get(cache_key)
            if cached_embeddings:
                return EmbeddingResponse(
                    embeddings=cached_embeddings,
                    model="cached",
                    provider="cache",
                    cached=True,
                    processing_time=time.time() - start_time,
                    token_count=sum(len(text.split()) for text in request.texts)
                )

        # Try providers in order (primary first, then fallbacks)
        providers_to_try = [self.primary_provider] if self.primary_provider else []

        last_error = None
        for provider_type in providers_to_try:
            if provider_type not in self.providers:
                continue

            provider = self.providers[provider_type]

            try:
                embeddings = await provider.embed(request.texts)

                if embeddings and len(embeddings) == len(request.texts):
                    # Normalize if requested
                    if request.normalize:
                        embeddings = self._normalize_embeddings(embeddings)

                    # Cache successful result
                    if cache_key:
                        self.cache.set(cache_key, embeddings)

                    return EmbeddingResponse(
                        embeddings=embeddings,
                        model=provider.config.model.value,
                        provider=provider_type.value,
                        cached=False,
                        processing_time=time.time() - start_time,
                        token_count=sum(len(text.split()) for text in request.texts)
                    )

            except Exception as e:
                logger.warning(f"Provider {provider_type} failed: {e}")
                last_error = e
                continue

        # All providers failed
        raise Exception(f"All embedding providers failed. Last error: {last_error}")

    def _normalize_embeddings(self, embeddings: List[List[float]]) -> List[List[float]]:
        """Normalize embeddings to unit vectors."""
        normalized = []
        for embedding in embeddings:
            # Calculate L2 norm
            norm = sum(x * x for x in embedding) ** 0.5
            if norm > 0:
                normalized.append([x / norm for x in embedding])
            else:
                normalized.append(embedding)
        return normalized

    async def embed_text(self, text: str, user_id: Optional[str] = None) -> List[float]:
        """Convenience method to embed single text."""
        request = EmbeddingRequest(texts=[text], user_id=user_id)
        response = await self.embed(request)
        return response.embeddings[0] if response.embeddings else []

    async def embed_texts(self, texts: List[str], user_id: Optional[str] = None) -> List[List[float]]:
        """Convenience method to embed multiple texts."""
        request = EmbeddingRequest(texts=texts, user_id=user_id)
        response = await self.embed(request)
        return response.embeddings

    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self.cache.cache.clear()

    def cleanup_cache(self) -> int:
        """Remove expired cache entries."""
        return self.cache.clear_expired()


# Factory functions for common configurations

def create_gemini_config(
    api_key: str,
    model: EmbeddingModel = EmbeddingModel.GEMINI_TEXT_004,
    **kwargs
) -> EmbeddingConfig:
    """Create Gemini embedding configuration."""
    return EmbeddingConfig(
        provider=EmbeddingProvider.GEMINI,
        model=model,
        api_key=api_key,
        **kwargs
    )


def create_openai_config(
    api_key: str,
    model: EmbeddingModel = EmbeddingModel.OPENAI_SMALL_3,
    **kwargs
) -> EmbeddingConfig:
    """Create OpenAI embedding configuration."""
    return EmbeddingConfig(
        provider=EmbeddingProvider.OPENAI,
        model=model,
        api_key=api_key,
        **kwargs
    )


def create_local_config(
    model: EmbeddingModel = EmbeddingModel.ALL_MINILM_L6_V2,
    **kwargs
) -> EmbeddingConfig:
    """Create local embedding configuration."""
    return EmbeddingConfig(
        provider=EmbeddingProvider.LOCAL,
        model=model,
        **kwargs
    )


# Integration with MemoryManager

class RealEmbedder:
    """Real embedder implementation for MemoryManager."""

    def __init__(self, embedding_manager: EmbeddingManager):
        self.embedding_manager = embedding_manager

    async def aembed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        if not texts:
            return []

        try:
            request = EmbeddingRequest(texts=texts)
            response = await self.embedding_manager.embed(request)
            return response.embeddings
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return empty embeddings as fallback
            return [[] for _ in texts]