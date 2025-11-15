"""Test case_create command locally to debug issue."""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from core.groupagents.mega_agent import (CommandType, MegaAgent,
                                         MegaAgentCommand, UserRole)
from core.memory.memory_manager import MemoryManager

load_dotenv()


async def test_case_create():
    """Test case creation."""
    print("Initializing MegaAgent...")
    memory_manager = MemoryManager()
    mega_agent = MegaAgent(memory_manager=memory_manager)

    print("\nCreating case command...")
    command = MegaAgentCommand(
        user_id="test_user",
        command_type=CommandType.CASE,
        action="create",
        payload={"title": "Тестовый кейс", "description": "описание"},
        context={"thread_id": "test_thread"},
    )

    print(f"Command created: {command}")
    print("\nExecuting command...")

    try:
        response = await asyncio.wait_for(
            mega_agent.handle_command(command, user_role=UserRole.LAWYER), timeout=10.0
        )
        print("\nResponse received:")
        print(f"  Success: {response.success}")
        print(f"  Result: {response.result}")
        print(f"  Error: {response.error}")
    except TimeoutError:
        print("\n❌ Command timed out after 10 seconds!")
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_case_create())
