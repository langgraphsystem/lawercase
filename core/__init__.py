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

# Group Agents
from .groupagents import *

# Memory System с Real Embeddings
from .memory import *
from .embeddings import *

# Security & RBAC
from .security import *

# Performance & Caching
from .performance import *

# Testing & Quality
from .testing import *

# Monitoring & Observability
from .monitoring import *

# Deployment & DevOps
from .deployment import *

# Infrastructure
from .infrastructure import *

# Config
from .config import *

__all__ = [
    # Core system info
    "__version__",
    "__author__",
]