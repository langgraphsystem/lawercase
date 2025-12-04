"""RFE (Request For Evidence) knowledge store with proper pgvector support.

This module provides semantic search over RFE knowledge base using SQLAlchemy ORM
with pgvector. It avoids raw SQL queries that cause syntax errors with asyncpg.

The issue with raw SQL like:
    SELECT ... 1 - (embedding <=> :embedding::vector) as similarity

Is that asyncpg expects $1, $2 positional parameters, not :name named parameters.
The double colon (::) for type casting conflicts with the :name parameter syntax.

Solution: Use SQLAlchemy ORM methods which properly handle parameter binding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from .connection import get_db_manager
from .models import RFEKnowledgeDB

if TYPE_CHECKING:
    pass


@dataclass
class RFEKnowledgeResult:
    """Result from RFE knowledge similarity search."""

    id: str
    criterion: str
    issue_type: str
    uscis_quote: str
    problem_description: str
    success_response: str
    similarity: float
    metadata: dict[str, Any]


class RFEKnowledgeStore:
    """
    RFE Knowledge Store with pgvector semantic search.

    Provides semantic similarity search over RFE (Request For Evidence)
    patterns from USCIS for EB-1A immigration petitions.

    Uses SQLAlchemy ORM for all database operations to avoid
    asyncpg parameter binding issues with raw SQL.

    Example:
        >>> store = RFEKnowledgeStore()
        >>> results = await store.search_similar(
        ...     query_embedding=[0.1, 0.2, ...],  # 1536-dim vector
        ...     limit=10
        ... )
        >>> for result in results:
        ...     print(f"{result.criterion}: {result.similarity:.2f}")
    """

    def __init__(self) -> None:
        """Initialize RFE Knowledge Store."""
        self.db = get_db_manager()

    async def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 10,
        criterion: str | None = None,
        min_similarity: float = 0.0,
    ) -> list[RFEKnowledgeResult]:
        """
        Search for similar RFE knowledge entries using pgvector cosine distance.

        Uses SQLAlchemy ORM to properly handle pgvector operations without
        raw SQL parameter binding issues.

        Args:
            query_embedding: Query vector (1536 dimensions)
            limit: Maximum number of results
            criterion: Optional filter by EB-1A criterion
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of RFEKnowledgeResult sorted by similarity (descending)

        Example:
            >>> results = await store.search_similar(
            ...     query_embedding=embedder.embed("extraordinary ability evidence"),
            ...     limit=5,
            ...     criterion="awards"
            ... )
        """
        # Use SQLAlchemy ORM cosine_distance method
        # This properly handles parameter binding for asyncpg
        distance = RFEKnowledgeDB.embedding.cosine_distance(query_embedding)

        stmt = (
            select(RFEKnowledgeDB, distance.label("distance"))
            .where(RFEKnowledgeDB.embedding.isnot(None))
            .order_by(distance)
            .limit(limit)
        )

        # Optional criterion filter
        if criterion:
            stmt = stmt.where(RFEKnowledgeDB.criterion == criterion)

        async with self.db.session() as session:
            result = await session.execute(stmt)
            rows = result.all()

        results: list[RFEKnowledgeResult] = []
        for db_record, distance_value in rows:
            # Convert cosine distance to similarity (1 - distance)
            similarity = max(0.0, 1.0 - float(distance_value or 0.0))

            if similarity < min_similarity:
                continue

            results.append(
                RFEKnowledgeResult(
                    id=str(db_record.id),
                    criterion=db_record.criterion,
                    issue_type=db_record.issue_type,
                    uscis_quote=db_record.uscis_quote,
                    problem_description=db_record.problem_description,
                    success_response=db_record.success_response,
                    similarity=similarity,
                    metadata=db_record.metadata_json or {},
                )
            )

        return results

    async def get_by_criterion(
        self,
        criterion: str,
        limit: int = 20,
    ) -> list[RFEKnowledgeResult]:
        """
        Get RFE knowledge entries by criterion without embedding search.

        Args:
            criterion: EB-1A criterion (e.g., "awards", "membership")
            limit: Maximum number of results

        Returns:
            List of RFEKnowledgeResult
        """
        stmt = (
            select(RFEKnowledgeDB)
            .where(RFEKnowledgeDB.criterion == criterion)
            .order_by(RFEKnowledgeDB.created_at.desc())
            .limit(limit)
        )

        async with self.db.session() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [
            RFEKnowledgeResult(
                id=str(row.id),
                criterion=row.criterion,
                issue_type=row.issue_type,
                uscis_quote=row.uscis_quote,
                problem_description=row.problem_description,
                success_response=row.success_response,
                similarity=1.0,  # No embedding search, full match
                metadata=row.metadata_json or {},
            )
            for row in rows
        ]

    async def insert(
        self,
        criterion: str,
        issue_type: str,
        uscis_quote: str,
        problem_description: str,
        success_response: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Insert a new RFE knowledge entry.

        Args:
            criterion: EB-1A criterion
            issue_type: Type of RFE issue
            uscis_quote: Direct quote from USCIS
            problem_description: Description of the problem
            success_response: Successful response template
            embedding: Optional embedding vector (1536 dims)
            metadata: Optional metadata

        Returns:
            ID of the created record
        """
        record = RFEKnowledgeDB(
            criterion=criterion,
            issue_type=issue_type,
            uscis_quote=uscis_quote,
            problem_description=problem_description,
            success_response=success_response,
            embedding=embedding,
            metadata_json=metadata or {},
        )

        async with self.db.session() as session:
            session.add(record)
            await session.flush()
            record_id = str(record.id)

        return record_id

    async def update_embedding(
        self,
        record_id: str,
        embedding: list[float],
        embedding_model: str = "text-embedding-3-large",
    ) -> bool:
        """
        Update the embedding for an existing RFE knowledge entry.

        Args:
            record_id: UUID of the record
            embedding: New embedding vector
            embedding_model: Model used to generate embedding

        Returns:
            True if updated, False if record not found
        """
        async with self.db.session() as session:
            stmt = select(RFEKnowledgeDB).where(RFEKnowledgeDB.id == UUID(record_id))
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                return False

            record.embedding = embedding
            record.embedding_model = embedding_model

        return True

    async def count(self, criterion: str | None = None) -> int:
        """
        Count RFE knowledge entries.

        Args:
            criterion: Optional filter by criterion

        Returns:
            Number of entries
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(RFEKnowledgeDB)

        if criterion:
            stmt = stmt.where(RFEKnowledgeDB.criterion == criterion)

        async with self.db.session() as session:
            result = await session.execute(stmt)
            return int(result.scalar() or 0)

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            await self.count()
            return True
        except Exception:
            return False


# Factory function
def create_rfe_knowledge_store() -> RFEKnowledgeStore:
    """Create a new RFE Knowledge Store instance."""
    return RFEKnowledgeStore()


__all__ = ["RFEKnowledgeResult", "RFEKnowledgeStore", "create_rfe_knowledge_store"]
