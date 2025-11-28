"""Database connection manager for PostgreSQL with async support."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_storage_config

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class DatabaseManager:
    """
    Async PostgreSQL connection manager with pooling.

    Features:
    - Connection pooling with configurable limits
    - Automatic session management with context managers
    - Health checks
    - Graceful shutdown

    Example:
        >>> db = DatabaseManager()
        >>> async with db.session() as session:
        ...     result = await session.execute(select(CaseDB))
        >>> await db.close()
    """

    def __init__(self):
        self.config = get_storage_config()
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def get_engine(self) -> AsyncEngine:
        """
        Get or create async SQLAlchemy engine.

        Returns:
            AsyncEngine instance with connection pooling

        Example:
            >>> db = DatabaseManager()
            >>> engine = db.get_engine()
            >>> engine.url
            postgresql+asyncpg://...
        """
        if self._engine is None:
            # Add SSL and connection parameters for Supabase compatibility
            connect_args = {
                # NOTE: JIT parameter removed for pgbouncer compatibility (port 6543)
                # pgbouncer doesn't support server_settings like "jit": "off"
                "ssl": "prefer",  # Use SSL if available
                "timeout": 30,  # Connection timeout
                # PgBouncer in transaction/statement mode breaks prepared statements.
                # Disable asyncpg statement cache to avoid "prepared statement already exists".
                "statement_cache_size": 0,
            }

            self._engine = create_async_engine(
                str(self.config.postgres_dsn),
                echo=self.config.echo_sql,  # Log SQL queries if enabled
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=False,  # Disabled for pgbouncer compatibility
                connect_args=connect_args,
            )
        return self._engine

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Get or create session factory.

        Returns:
            Session factory for creating database sessions

        Example:
            >>> db = DatabaseManager()
            >>> factory = db.get_session_factory()
            >>> async with factory() as session:
            ...     await session.execute(...)
        """
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,  # Don't expire objects after commit
            )
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions with automatic commit/rollback.

        Yields:
            AsyncSession for database operations

        Example:
            >>> db = DatabaseManager()
            >>> async with db.session() as session:
            ...     case = CaseDB(user_id="u1", title="Test")
            ...     session.add(case)
            ...     # Auto-commit on exit
        """
        factory = self.get_session_factory()
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """
        Close all database connections gracefully.

        Example:
            >>> db = DatabaseManager()
            >>> # ... use database ...
            >>> await db.close()
        """
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    async def health_check(self) -> bool:
        """
        Check database connectivity.

        Returns:
            True if database is accessible, False otherwise

        Example:
            >>> db = DatabaseManager()
            >>> is_healthy = await db.health_check()
            >>> print(is_healthy)
            True
        """
        try:
            from sqlalchemy import text

            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def create_schema(self) -> None:
        """
        Create 'mega_agent' schema if it doesn't exist.

        Example:
            >>> db = DatabaseManager()
            >>> await db.create_schema()
        """
        from sqlalchemy import text

        async with self.session() as session:
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS mega_agent"))

    async def create_all_tables(self) -> None:
        """
        Create all tables defined in models.

        Warning: This is for development only. Use Alembic migrations in production.

        Example:
            >>> db = DatabaseManager()
            >>> await db.create_schema()
            >>> await db.create_all_tables()
        """
        from .models import Base

        async with self.get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all_tables(self) -> None:
        """
        Drop all tables (DESTRUCTIVE - development only).

        Warning: This will delete all data. Only use in development.

        Example:
            >>> db = DatabaseManager()
            >>> await db.drop_all_tables()  # CAUTION!
        """
        from .models import Base

        async with self.get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# Global singleton instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance.

    Returns:
        Shared DatabaseManager instance

    Example:
        >>> db = get_db_manager()
        >>> async with db.session() as session:
        ...     # Use session
        ...     pass
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        AsyncSession for use in FastAPI routes

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/cases")
        >>> async def list_cases(session: AsyncSession = Depends(get_session)):
        ...     result = await session.execute(select(CaseDB))
        ...     return result.scalars().all()
    """
    manager = get_db_manager()
    async with manager.session() as session:
        yield session
