"""
EB-1A Knowledge Base Access for Agents.

Provides functions to query the USCIS EB-1A knowledge base
stored in Supabase. Contains official forms, policy documents,
and guides for EB-1A Extraordinary Ability visa.

Usage:
    from core.knowledge.eb1a_knowledge_base import EB1AKnowledgeBase

    kb = EB1AKnowledgeBase()

    # Search by keyword
    results = await kb.search("extraordinary ability criteria")

    # Get specific document type
    forms = await kb.get_by_document_type("forms")

    # Full-text search
    results = await kb.fulltext_search("I-140 filing requirements")
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class EB1AKnowledgeBase:
    """
    Access to EB-1A USCIS knowledge base in Supabase.

    Contains 571 chunks from 23 official documents:
    - Forms: I-140, I-907, I-485, G-1055, etc.
    - Policy: Policy Manual Vol.6, Kazarian case
    - Guides: Filing addresses, premium processing, fees

    Example:
        >>> kb = EB1AKnowledgeBase()
        >>> results = await kb.search("10 criteria")
        >>> for r in results:
        ...     print(r['document_name'], r['content'][:100])
    """

    NAMESPACE = "eb1a"
    TABLE = "knowledge_base"

    def __init__(self):
        """Initialize Supabase connection."""
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY required")

        self.client = create_client(url, key)

    async def search(
        self,
        query: str,
        limit: int = 10,
        document_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search knowledge base by keyword (ILIKE).

        Args:
            query: Search query string
            limit: Maximum results to return
            document_type: Filter by type (forms, policy, guides)

        Returns:
            List of matching chunks with metadata

        Example:
            >>> results = await kb.search("extraordinary ability")
            >>> print(len(results))  # Up to 10 results
        """
        q = (
            self.client.table(self.TABLE)
            .select("id, content, metadata, created_at")
            .eq("namespace", self.NAMESPACE)
            .ilike("content", f"%{query}%")
            .limit(limit)
        )

        if document_type:
            q = q.eq("metadata->>document_type", document_type)

        result = q.execute()

        return [
            {
                "id": row["id"],
                "content": row["content"],
                "document_name": row.get("metadata", {}).get("document_name", "Unknown"),
                "document_type": row.get("metadata", {}).get("document_type", ""),
                "document_id": row.get("metadata", {}).get("document_id", ""),
                "description": row.get("metadata", {}).get("description", ""),
                "chunk_index": row.get("metadata", {}).get("chunk_index", 0),
                "total_chunks": row.get("metadata", {}).get("total_chunks", 1),
            }
            for row in result.data
        ]

    async def fulltext_search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Full-text search using PostgreSQL FTS.

        Args:
            query: Search query (supports AND, OR, NOT)
            limit: Maximum results

        Returns:
            List of matching chunks ranked by relevance

        Example:
            >>> results = await kb.fulltext_search("I-140 AND premium")
        """
        # Convert to tsquery format
        tsquery = " & ".join(query.split())

        result = self.client.rpc(
            "search_knowledge_base", {"search_query": tsquery, "result_limit": limit}
        ).execute()

        # Fallback to ILIKE if RPC not available
        if not result.data:
            return await self.search(query, limit)

        return result.data

    async def get_by_document_type(
        self,
        document_type: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get all chunks from a specific document type.

        Args:
            document_type: One of 'forms', 'policy', 'guides'
            limit: Maximum chunks to return

        Returns:
            List of document chunks

        Example:
            >>> forms = await kb.get_by_document_type("forms")
            >>> policies = await kb.get_by_document_type("policy")
        """
        result = (
            self.client.table(self.TABLE)
            .select("id, content, metadata")
            .eq("namespace", self.NAMESPACE)
            .eq("metadata->>document_type", document_type)
            .limit(limit)
            .execute()
        )

        return [
            {
                "id": row["id"],
                "content": row["content"],
                "document_name": row.get("metadata", {}).get("document_name"),
                "document_id": row.get("metadata", {}).get("document_id"),
            }
            for row in result.data
        ]

    async def get_document(
        self,
        document_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get all chunks for a specific document.

        Args:
            document_id: Document ID (e.g., 'form-i140', 'policy-vol6-partF-ch2')

        Returns:
            List of all chunks for this document in order

        Example:
            >>> chunks = await kb.get_document("form-i140")
            >>> full_text = " ".join(c['content'] for c in chunks)
        """
        result = (
            self.client.table(self.TABLE)
            .select("id, content, metadata")
            .eq("namespace", self.NAMESPACE)
            .eq("metadata->>document_id", document_id)
            .order("metadata->>chunk_index")
            .execute()
        )

        return [
            {
                "id": row["id"],
                "content": row["content"],
                "chunk_index": row.get("metadata", {}).get("chunk_index", 0),
                "document_name": row.get("metadata", {}).get("document_name"),
            }
            for row in result.data
        ]

    async def get_criteria_info(
        self,
        criterion_number: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get information about EB-1A criteria.

        Args:
            criterion_number: 1-10 for specific criterion, None for all

        Returns:
            Relevant chunks about criteria requirements

        Example:
            >>> # Get info about criterion 5 (Original Contributions)
            >>> info = await kb.get_criteria_info(5)
        """
        criteria_keywords = {
            1: "awards prizes excellence",
            2: "membership associations outstanding",
            3: "published material media",
            4: "judging judge panel review",
            5: "original contributions major significance",
            6: "scholarly articles publications",
            7: "artistic exhibitions showcases",
            8: "leading critical role distinguished",
            9: "high salary remuneration",
            10: "commercial success performing arts",
        }

        if criterion_number and criterion_number in criteria_keywords:
            query = f"criterion {criteria_keywords[criterion_number]}"
        else:
            query = "10 criteria EB-1A extraordinary ability"

        return await self.search(query, limit=15)

    async def get_form_info(self, form_name: str) -> list[dict[str, Any]]:
        """
        Get information about a specific USCIS form.

        Args:
            form_name: Form name (e.g., 'I-140', 'I-907', 'G-1055')

        Returns:
            Chunks related to the form

        Example:
            >>> info = await kb.get_form_info("I-140")
        """
        return await self.search(form_name, limit=20, document_type="forms")

    async def get_fees_info(self) -> list[dict[str, Any]]:
        """
        Get current filing fees information.

        Returns:
            Chunks about USCIS fees
        """
        return await self.search("filing fee premium processing", limit=10)

    async def get_kazarian_analysis(self) -> list[dict[str, Any]]:
        """
        Get information about Kazarian two-step analysis.

        Returns:
            Chunks about Kazarian v. USCIS case and two-step framework
        """
        return await self.search("Kazarian two-step analysis", limit=15)

    async def get_stats(self) -> dict[str, Any]:
        """
        Get knowledge base statistics.

        Returns:
            Stats about the knowledge base
        """
        result = (
            self.client.table(self.TABLE)
            .select("id, metadata", count="exact")
            .eq("namespace", self.NAMESPACE)
            .execute()
        )

        # Count unique documents
        docs = set()
        doc_types = {}
        for row in result.data:
            doc_name = row.get("metadata", {}).get("document_name")
            doc_type = row.get("metadata", {}).get("document_type")
            if doc_name:
                docs.add(doc_name)
            if doc_type:
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        return {
            "total_chunks": result.count or len(result.data),
            "unique_documents": len(docs),
            "documents": list(docs),
            "by_type": doc_types,
            "namespace": self.NAMESPACE,
        }


# Convenience function for quick access
async def search_eb1a_knowledge(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Quick search of EB-1A knowledge base.

    Args:
        query: Search query
        limit: Max results

    Returns:
        List of matching chunks

    Example:
        >>> from core.knowledge.eb1a_knowledge_base import search_eb1a_knowledge
        >>> results = await search_eb1a_knowledge("premium processing")
    """
    kb = EB1AKnowledgeBase()
    return await kb.search(query, limit)


__all__ = [
    "EB1AKnowledgeBase",
    "search_eb1a_knowledge",
]
