"""
Knowledge Base Module.

Provides access to domain-specific knowledge bases stored in Supabase.
"""

from __future__ import annotations

from .eb1a_knowledge_base import EB1AKnowledgeBase, search_eb1a_knowledge

__all__ = [
    "EB1AKnowledgeBase",
    "search_eb1a_knowledge",
]
