"""Test Supabase database connection and check if cases table exists."""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()


async def test_supabase_connection():
    """Test connection to Supabase and check if cases table exists."""

    # Get database URL from environment
    database_url = os.getenv("POSTGRES_DSN")
    if not database_url:
        print("❌ POSTGRES_DSN not found in .env")
        print(
            "   Please set POSTGRES_DSN (e.g. 'postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB')"  # pragma: allowlist secret
        )
        return

    print("\n" + "=" * 60)
    print("🔌 SUPABASE DATABASE CONNECTION TEST")
    print("=" * 60 + "\n")

    print(f"Database URL: {database_url.split('@')[0]}@***")  # Hide credentials

    try:
        # Create async engine
        engine = create_async_engine(database_url, echo=False)

        # Create session maker
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Test 1: Basic connection
            print("✅ Test 1: Basic connection...")
            result = await session.execute(text("SELECT version()"))
            version = result.scalar_one()
            print(f"   PostgreSQL version: {version.split(',')[0]}")
            print()

            # Test 2: Check if mega_agent schema exists
            print("✅ Test 2: Check mega_agent schema...")
            result = await session.execute(
                text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'mega_agent'"
                )
            )
            schema = result.scalar_one_or_none()
            if schema:
                print("   ✅ Schema 'mega_agent' exists")
            else:
                print("   ❌ Schema 'mega_agent' NOT FOUND")
                print("   Creating schema...")
                await session.execute(text("CREATE SCHEMA IF NOT EXISTS mega_agent"))
                await session.commit()
                print("   ✅ Schema created")
            print()

            # Test 3: Check if cases table exists
            print("✅ Test 3: Check cases table...")
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'mega_agent' AND table_name = 'cases'"
                )
            )
            table = result.scalar_one_or_none()
            if table:
                print("   ✅ Table 'mega_agent.cases' exists")

                # Get table structure
                result = await session.execute(
                    text(
                        "SELECT column_name, data_type, is_nullable "
                        "FROM information_schema.columns "
                        "WHERE table_schema = 'mega_agent' AND table_name = 'cases' "
                        "ORDER BY ordinal_position"
                    )
                )
                columns = result.all()
                print(f"   Table has {len(columns)} columns:")
                for col in columns:
                    nullable = "NULL" if col.is_nullable == "YES" else "NOT NULL"
                    print(f"     - {col.column_name}: {col.data_type} ({nullable})")

                # Count existing cases
                result = await session.execute(text("SELECT COUNT(*) FROM mega_agent.cases"))
                count = result.scalar_one()
                print(f"   Cases in database: {count}")
            else:
                print("   ❌ Table 'mega_agent.cases' NOT FOUND")
                print("   You need to run migrations to create the table")
                print("   Run: alembic upgrade head")
            print()

            # Test 4: Check other tables
            print("✅ Test 4: Check other tables...")
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'mega_agent' "
                    "ORDER BY table_name"
                )
            )
            tables = result.scalars().all()
            if tables:
                print(f"   Found {len(tables)} table(s) in mega_agent schema:")
                for table_name in tables:
                    print(f"     - {table_name}")
            else:
                print("   No tables found in mega_agent schema")
            print()

        await engine.dispose()

        print("=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_supabase_connection())
