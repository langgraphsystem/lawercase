"""
Core module для mega_agent_pro - Comprehensive Legal AI System.

This module provides all core infrastructure components:
- Multi-agent orchestration system
- Advanced memory management с real embeddings
- Security & RBAC framework
- Performance optimization с multi-level caching
- Testing & quality assurance framework
- Comprehensive monitoring & observability
- Deployment & DevOps automation
- Workflow orchestration system
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

# LLM Router
try:
    from .llm_router import *
except ImportError:
    pass

# Simple Embedder
try:
    from .simple_embedder import *
except ImportError:
    pass

# Basic RAG
try:
    from .basic_rag import *
except ImportError:
    pass

# Group Agents
try:
    from .groupagents import *
except ImportError:
    pass

# Memory System с Real Embeddings
try:
    from .memory import *
    from .embeddings import *
except ImportError:
    pass

# Security & RBAC
try:
    from .security import *
except ImportError:
    pass

# Performance & Caching
try:
    from .performance import *
except ImportError:
    pass

# Testing & Quality
try:
    from .testing import *
except ImportError:
    pass

# Monitoring & Observability
try:
    from .monitoring import *
except ImportError:
    pass

# Deployment & DevOps
try:
    from .deployment import *
except ImportError:
    pass

# Infrastructure
try:
    from .infrastructure import *
except ImportError:
    pass

# Config
try:
    from .config import *
except ImportError:
    pass

__all__ = [
    # Core system info
    "__version__",
    "__author__",
]