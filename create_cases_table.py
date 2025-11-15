"""Create only the cases table in Supabase (without vector dependencies)."""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()


async def create_cases_table():
    """Create cases table manually without vector dependencies."""

    database_url = os.getenv("POSTGRES_DSN")
    if not database_url:
        print("❌ POSTGRES_DSN not found in .env")
        return

    print("\n" + "=" * 60)
    print("📦 CREATING CASES TABLE")
    print("=" * 60 + "\n")

    try:
        engine = create_async_engine(database_url, echo=False)

        async with engine.begin() as conn:
            # Enable pgvector extension (needed for Supabase)
            print("✅ Enabling pgvector extension...")
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                print("   pgvector extension enabled")
            except Exception as e:
                print(f"   Warning: Could not enable pgvector: {e}")

            # Create cases table
            print("\n✅ Creating cases table...")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS mega_agent.cases (
                case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                case_type VARCHAR(100),
                data JSONB NOT NULL DEFAULT '{}'::jsonb,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                deleted_at TIMESTAMP WITH TIME ZONE,

                CONSTRAINT case_title_not_empty CHECK (length(title) > 0),
                CONSTRAINT case_status_valid CHECK (
                    status IN ('draft', 'open', 'in_progress', 'closed', 'archived')
                )
            )
            """
            await conn.execute(text(create_table_sql))
            print("   cases table created")

            # Create indexes
            print("\n✅ Creating indexes...")

            await conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_cases_user_id
                ON mega_agent.cases(user_id)
            """
                )
            )
            print("   idx_cases_user_id created")

            await conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_cases_status
                ON mega_agent.cases(status)
            """
                )
            )
            print("   idx_cases_status created")

            await conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_cases_created
                ON mega_agent.cases(created_at)
            """
                )
            )
            print("   idx_cases_created created")

            await conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_cases_data
                ON mega_agent.cases USING gin(data)
            """
                )
            )
            print("   idx_cases_data created")

            await conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_cases_active
                ON mega_agent.cases(user_id, status)
                WHERE deleted_at IS NULL
            """
                )
            )
            print("   idx_cases_active created")

            # Create updated_at trigger
            print("\n✅ Creating updated_at trigger...")
            await conn.execute(
                text(
                    """
                CREATE OR REPLACE FUNCTION mega_agent.update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = now();
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """
                )
            )

            await conn.execute(
                text(
                    """
                DROP TRIGGER IF EXISTS update_cases_updated_at ON mega_agent.cases
            """
                )
            )

            await conn.execute(
                text(
                    """
                CREATE TRIGGER update_cases_updated_at
                BEFORE UPDATE ON mega_agent.cases
                FOR EACH ROW
                EXECUTE FUNCTION mega_agent.update_updated_at_column()
            """
                )
            )
            print("   updated_at trigger created")

        await engine.dispose()

        print("\n" + "=" * 60)
        print("✅ Cases table created successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(create_cases_table())
