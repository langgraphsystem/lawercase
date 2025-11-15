"""Test script to verify CaseAgent database integration."""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import select, text

from core.groupagents.mega_agent import (CommandType, MegaAgent,
                                         MegaAgentCommand, UserRole)
from core.memory.memory_manager import MemoryManager
from core.storage.connection import get_db_manager
from core.storage.models import CaseDB

load_dotenv()


async def test_database_integration():
    """Test case creation with database persistence."""

    print("\n" + "=" * 60)
    print("🧪 TESTING CASEAGENT DATABASE INTEGRATION")
    print("=" * 60 + "\n")

    # Check if POSTGRES_DSN is configured
    postgres_dsn = os.getenv("POSTGRES_DSN")
    if not postgres_dsn:
        print("❌ POSTGRES_DSN not configured in .env")
        print("   Skipping database test")
        return

    print(f"✅ POSTGRES_DSN configured: {postgres_dsn.split('@')[0]}@***\n")

    # Initialize MegaAgent (which will create CaseAgent with DatabaseManager)
    print("📦 Initializing MegaAgent...")
    memory_manager = MemoryManager()
    mega_agent = MegaAgent(memory_manager=memory_manager)

    if mega_agent.db_manager is None:
        print("❌ DatabaseManager not initialized")
        return

    print("✅ DatabaseManager initialized")
    print(f"✅ CaseAgent use_database: {mega_agent.case_agent.use_database}\n")

    # Test 1: Create a case
    print("=" * 60)
    print("TEST 1: Create case with database persistence")
    print("=" * 60 + "\n")

    command = MegaAgentCommand(
        user_id="test_user",
        command_type=CommandType.CASE,
        action="create",
        payload={
            "title": "Test Database Integration",
            "description": "Testing CaseAgent database persistence",
            "case_type": "test",
        },
        context={"thread_id": "test_thread"},
    )

    print("Executing command...")
    response = await mega_agent.handle_command(command, user_role=UserRole.LAWYER)

    print("\nResponse:")
    print(f"  Success: {response.success}")
    print(f"  Result: {response.result}")
    print(f"  Error: {response.error}")

    if not response.success:
        print("\n❌ Case creation failed!")
        return

    # Extract case_id
    case_result = response.result.get("case_result", {})
    case_id = response.result.get("case_id") or case_result.get("case_id")

    if not case_id:
        print("\n❌ No case_id in response!")
        return

    print(f"\n✅ Case created with ID: {case_id}")

    # Test 2: Verify case exists in database
    print("\n" + "=" * 60)
    print("TEST 2: Verify case in database")
    print("=" * 60 + "\n")

    db_manager = get_db_manager()

    async with db_manager.session() as session:
        # Count cases in database
        count_stmt = select(text("COUNT(*)")).select_from(CaseDB.__table__)
        result = await session.execute(count_stmt)
        count = result.scalar()
        print(f"Total cases in database: {count}")

        # Get our specific case
        from uuid import UUID

        stmt = select(CaseDB).where(CaseDB.case_id == UUID(case_id))
        result = await session.execute(stmt)
        db_case = result.scalar_one_or_none()

        if db_case:
            print("\n✅ Case found in database!")
            print(f"  Case ID: {db_case.case_id}")
            print(f"  Title: {db_case.title}")
            print(f"  Description: {db_case.description}")
            print(f"  Status: {db_case.status}")
            print(f"  Case Type: {db_case.case_type}")
            print(f"  Created At: {db_case.created_at}")
            print(f"  Updated At: {db_case.updated_at}")
            print(f"  Version: {db_case.version}")
        else:
            print("\n❌ Case NOT found in database!")
            return

    # Test 3: Retrieve case through CaseAgent
    print("\n" + "=" * 60)
    print("TEST 3: Retrieve case through CaseAgent")
    print("=" * 60 + "\n")

    get_command = MegaAgentCommand(
        user_id="test_user",
        command_type=CommandType.CASE,
        action="get",
        payload={"case_id": case_id},
        context={"thread_id": "test_thread"},
    )

    print("Retrieving case...")
    get_response = await mega_agent.handle_command(get_command, user_role=UserRole.LAWYER)

    if get_response.success:
        retrieved_case = get_response.result.get("case_result", {})
        print("\n✅ Case retrieved successfully!")
        print(f"  Title: {retrieved_case.get('title')}")
        print(f"  Status: {retrieved_case.get('status')}")
    else:
        print(f"\n❌ Failed to retrieve case: {get_response.error}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - DATABASE INTEGRATION WORKING!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_database_integration())
