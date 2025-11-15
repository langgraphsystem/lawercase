"""Direct test of CaseAgent.acreate_case method."""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from core.groupagents.case_agent import CaseAgent
from core.memory.memory_manager import MemoryManager
from core.storage.connection import get_db_manager

load_dotenv()


async def test_direct():
    """Test acreate_case directly."""

    print("\n🧪 DIRECT CASEAGENT TEST\n")

    # Get DatabaseManager
    try:
        db_manager = get_db_manager()
        print("✅ DatabaseManager initialized")
    except Exception as e:
        print(f"❌ DatabaseManager failed: {e}")
        db_manager = None

    # Create CaseAgent
    memory = MemoryManager()
    case_agent = CaseAgent(memory_manager=memory, db_manager=db_manager)
    print(f"✅ CaseAgent created (use_database={case_agent.use_database})\n")

    # Create case directly
    case_data = {
        "title": "Direct Test Case",
        "description": "Testing acreate_case directly",
        "case_type": "other",
        "client_id": "test_client_123",
    }

    print(f"📝 Creating case with data: {case_data}\n")

    try:
        record = await case_agent.acreate_case(user_id="test_user", case_data=case_data)

        print("✅ CASE CREATED SUCCESSFULLY!")
        print(f"  Case ID: {record.case_id}")
        print(f"  Title: {record.title}")
        print(f"  Description: {record.description}")
        print(f"  Status: {record.status}")
        print(f"  Case Type: {record.case_type}")
        print(f"  Created By: {record.created_by}")
        print(f"\n  Full record: {record.model_dump()}")

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct())
