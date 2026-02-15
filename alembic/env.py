"""Alembic environment configuration for async SQLAlchemy migrations.

This file configures Alembic to work with:
- Async PostgreSQL (asyncpg)
- pgvector extension
- Pydantic settings for database URL
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
import os
from pathlib import Path
import sys

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import models for autogenerate support
from core.storage.models import Base

# Alembic Config object
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from environment or settings.

    Priority:
    1. POSTGRES_DSN environment variable
    2. DATABASE_URL environment variable (Railway/Heroku style)

    Returns:
        PostgreSQL connection string for asyncpg
    """
    # Try POSTGRES_DSN first (our standard)
    url = os.getenv("POSTGRES_DSN")

    # Fallback to DATABASE_URL (Railway/Heroku)
    if not url:
        url = os.getenv("DATABASE_URL")
        if url and url.startswith("postgres://"):
            # Convert postgres:// to postgresql+asyncpg://
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url and url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if not url:
        raise ValueError(
            "Database URL not found. Set POSTGRES_DSN or DATABASE_URL environment variable."
        )

    # Ensure asyncpg driver is specified
    if not url.startswith("postgresql+asyncpg://"):
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit SQL to the script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table_schema="mega_agent",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within a connection context."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table_schema="mega_agent",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine.

    Creates an async Engine and associates a connection with the context.
    """
    # Get database URL
    url = get_database_url()

    # Configure engine
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    # Create async engine with connection pooling disabled for migrations
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Ensure pgvector extension exists
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Ensure schema exists
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS mega_agent"))

        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
