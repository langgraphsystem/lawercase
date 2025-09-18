"""
Configuration module for mega_agent_pro.

Centralized configuration management for different components and environments.
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    "EmbeddingConfigFactory",
    "EmbeddingEnvironment",
    "get_default_embedding_config",
    "get_production_embedding_config",
    "get_development_embedding_config",
    "get_testing_embedding_config",
]

from .embeddings_config import (
    EmbeddingConfigFactory,
    EmbeddingEnvironment,
    get_default_embedding_config,
    get_development_embedding_config,
    get_production_embedding_config,
    get_testing_embedding_config,
)