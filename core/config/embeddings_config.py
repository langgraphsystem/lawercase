"""
Configuration for real embeddings integration in mega_agent_pro.

Provides factory functions and configuration management for different
embedding providers and deployment scenarios.
"""

from __future__ import annotations

import os
from typing import List, Optional

from ..embeddings import (
    EmbeddingConfig,
    EmbeddingModel,
    EmbeddingProvider,
    create_gemini_config,
    create_local_config,
    create_openai_config,
)


class EmbeddingConfigFactory:
    """Factory for creating embedding configurations based on environment."""

    @staticmethod
    def create_production_config() -> List[EmbeddingConfig]:
        """Create production embedding configuration with fallbacks."""
        configs = []

        # Primary: Gemini (if API key available)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            configs.append(create_gemini_config(
                api_key=gemini_key,
                model=EmbeddingModel.GEMINI_TEXT_004,
                batch_size=100,
                rate_limit_per_minute=1000,
                cache_ttl_hours=24,
                fallback_providers=[EmbeddingProvider.OPENAI, EmbeddingProvider.LOCAL]
            ))

        # Secondary: OpenAI (if API key available)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            configs.append(create_openai_config(
                api_key=openai_key,
                model=EmbeddingModel.OPENAI_SMALL_3,
                batch_size=2048,  # OpenAI has higher batch limits
                rate_limit_per_minute=3000,
                cache_ttl_hours=24
            ))

        # Fallback: Local model (always available)
        configs.append(create_local_config(
            model=EmbeddingModel.ALL_MINILM_L6_V2,
            batch_size=32,  # Local processing typically smaller batches
            rate_limit_per_minute=10000,  # No API limits for local
            cache_ttl_hours=24
        ))

        return configs

    @staticmethod
    def create_development_config() -> List[EmbeddingConfig]:
        """Create development embedding configuration (local-first)."""
        configs = []

        # Primary: Local model for development
        configs.append(create_local_config(
            model=EmbeddingModel.ALL_MINILM_L6_V2,
            batch_size=16,
            rate_limit_per_minute=10000,
            cache_ttl_hours=1  # Shorter cache in development
        ))

        # Secondary: Gemini if available for testing
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            configs.append(create_gemini_config(
                api_key=gemini_key,
                model=EmbeddingModel.GEMINI_TEXT_004,
                batch_size=50,
                rate_limit_per_minute=100,  # Lower rate limits in dev
                cache_ttl_hours=1
            ))

        return configs

    @staticmethod
    def create_testing_config() -> List[EmbeddingConfig]:
        """Create testing embedding configuration (fast and reliable)."""
        return [
            create_local_config(
                model=EmbeddingModel.ALL_MINILM_L6_V2,
                batch_size=8,
                rate_limit_per_minute=10000,
                cache_ttl_hours=0,  # No caching in tests
                timeout=5.0  # Faster timeout for tests
            )
        ]

    @staticmethod
    def create_azure_config() -> List[EmbeddingConfig]:
        """Create Azure OpenAI embedding configuration."""
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")

        if not azure_key or not azure_endpoint:
            raise ValueError("Azure OpenAI requires AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")

        return [
            EmbeddingConfig(
                provider=EmbeddingProvider.AZURE_OPENAI,
                model=EmbeddingModel.OPENAI_SMALL_3,
                api_key=azure_key,
                api_base=azure_endpoint,
                api_version=azure_version,
                batch_size=2048,
                rate_limit_per_minute=3000,
                cache_ttl_hours=24
            )
        ]

    @staticmethod
    def create_custom_config(
        providers: List[str],
        api_keys: Optional[dict] = None,
        **kwargs
    ) -> List[EmbeddingConfig]:
        """Create custom embedding configuration.

        Args:
            providers: List of provider names ('gemini', 'openai', 'local')
            api_keys: Dict mapping provider names to API keys
            **kwargs: Additional configuration options

        Returns:
            List of embedding configurations
        """
        api_keys = api_keys or {}
        configs = []

        for provider in providers:
            if provider.lower() == "gemini":
                key = api_keys.get("gemini") or os.getenv("GEMINI_API_KEY")
                if key:
                    configs.append(create_gemini_config(
                        api_key=key,
                        **kwargs
                    ))

            elif provider.lower() == "openai":
                key = api_keys.get("openai") or os.getenv("OPENAI_API_KEY")
                if key:
                    configs.append(create_openai_config(
                        api_key=key,
                        **kwargs
                    ))

            elif provider.lower() == "local":
                configs.append(create_local_config(**kwargs))

        return configs


class EmbeddingEnvironment:
    """Environment detection and configuration selection."""

    @staticmethod
    def detect_environment() -> str:
        """Detect current environment based on environment variables."""
        env = os.getenv("ENVIRONMENT", "").lower()

        if env in ["prod", "production"]:
            return "production"
        elif env in ["dev", "development"]:
            return "development"
        elif env in ["test", "testing"]:
            return "testing"
        else:
            # Auto-detect based on available configurations
            if os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"):
                return "production"
            else:
                return "development"

    @staticmethod
    def get_config_for_environment(environment: Optional[str] = None) -> List[EmbeddingConfig]:
        """Get appropriate embedding configuration for environment."""
        env = environment or EmbeddingEnvironment.detect_environment()

        if env == "production":
            return EmbeddingConfigFactory.create_production_config()
        elif env == "development":
            return EmbeddingConfigFactory.create_development_config()
        elif env == "testing":
            return EmbeddingConfigFactory.create_testing_config()
        else:
            # Default to development
            return EmbeddingConfigFactory.create_development_config()


# Convenience functions for direct usage

def get_default_embedding_config() -> List[EmbeddingConfig]:
    """Get default embedding configuration for current environment."""
    return EmbeddingEnvironment.get_config_for_environment()


def get_production_embedding_config() -> List[EmbeddingConfig]:
    """Get production embedding configuration."""
    return EmbeddingConfigFactory.create_production_config()


def get_development_embedding_config() -> List[EmbeddingConfig]:
    """Get development embedding configuration."""
    return EmbeddingConfigFactory.create_development_config()


def get_testing_embedding_config() -> List[EmbeddingConfig]:
    """Get testing embedding configuration."""
    return EmbeddingConfigFactory.create_testing_config()


# Example usage configurations

EXAMPLE_CONFIGS = {
    "gemini_only": [
        create_gemini_config(
            api_key="your-gemini-api-key",
            model=EmbeddingModel.GEMINI_TEXT_004
        )
    ],

    "openai_only": [
        create_openai_config(
            api_key="your-openai-api-key",
            model=EmbeddingModel.OPENAI_SMALL_3
        )
    ],

    "local_only": [
        create_local_config(
            model=EmbeddingModel.ALL_MINILM_L6_V2
        )
    ],

    "hybrid_cloud_local": [
        create_gemini_config(
            api_key="your-gemini-api-key",
            model=EmbeddingModel.GEMINI_TEXT_004,
            fallback_providers=[EmbeddingProvider.LOCAL]
        ),
        create_local_config(
            model=EmbeddingModel.ALL_MINILM_L6_V2
        )
    ],

    "multi_provider": [
        create_gemini_config(
            api_key="your-gemini-api-key",
            model=EmbeddingModel.GEMINI_TEXT_004
        ),
        create_openai_config(
            api_key="your-openai-api-key",
            model=EmbeddingModel.OPENAI_SMALL_3
        ),
        create_local_config(
            model=EmbeddingModel.ALL_MINILM_L6_V2
        )
    ]
}