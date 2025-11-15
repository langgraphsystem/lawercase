"""Create all database tables in Supabase using SQLAlchemy models."""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

from core.storage.models import Base

load_dotenv()


async def create_tables():
    """Create all tables defined in Base metadata."""

    # Get database URL from environment
    database_url = os.getenv("POSTGRES_DSN")
    if not database_url:
        print("❌ POSTGRES_DSN not found in .env")
        return

    print("\n" + "=" * 60)
    print("📦 CREATING DATABASE TABLES")
    print("=" * 60 + "\n")

    print(f"Database URL: {database_url.split('@')[0]}@***")
    print()

    try:
        # Create async engine
        engine = create_async_engine(database_url, echo=True)

        # Create all tables
        print("Creating tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await engine.dispose()

        print("\n" + "=" * 60)
        print("✅ All tables created successfully!")
        print("=" * 60)
        print("\nCreated tables:")
        for table_name in Base.metadata.tables:
            print(f"  - {table_name}")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(create_tables())
