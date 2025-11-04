"""Storage layer for mega_agent_pro.

This module provides:
- PostgreSQL stores for metadata and audit trails
- Pinecone vector store for semantic search
- Cloudflare R2 for document storage
"""

from __future__ import annotations

__all__ = [
    "create_pinecone_store",
    "create_r2_storage",
    "create_voyage_embedder",
    "get_db_manager",
    "get_storage_config",
]
