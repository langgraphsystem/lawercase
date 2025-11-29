"""
Demo script showing how @ensure_case_exists decorator works
"""

from __future__ import annotations

import asyncio


# Simplified version of the decorator for demo purposes
def ensure_case_exists_demo(func):
    """
    Demo decorator showing the protection logic.
    """

    async def wrapper(case_id, *args, **kwargs):
        print(f"\n🔍 Checking if case {case_id} exists...")

        # Simulate case lookup
        case_exists = case_id in ["case-123", "case-456"]

        if not case_exists:
            print(f"⚠️  Case {case_id} NOT FOUND!")
            print(f"🔧 Auto-creating case {case_id}...")
            print(f"✅ Case {case_id} created successfully!")
        else:
            print(f"✅ Case {case_id} already exists")

        print(f"▶️  Executing handler: {func.__name__}")
        return await func(case_id, *args, **kwargs)

    return wrapper


# Example handlers with decorator
@ensure_case_exists_demo
async def intake_status(case_id):
    """Handler that shows intake status."""
    print(f"   📊 Showing status for case {case_id}")
    return f"Status for {case_id}"


@ensure_case_exists_demo
async def intake_resume(case_id):
    """Handler that resumes intake."""
    print(f"   ▶️  Resuming intake for case {case_id}")
    return f"Resumed {case_id}"


async def demo():
    """Run demo scenarios."""
    print("=" * 80)
    print("DEMO: @ensure_case_exists Decorator")
    print("=" * 80)

    print("\n📌 Scenario 1: Case exists (normal flow)")
    print("-" * 80)
    result = await intake_status("case-123")
    print(f"Result: {result}")

    print("\n📌 Scenario 2: Case missing (auto-recovery)")
    print("-" * 80)
    result = await intake_status("case-orphan-999")
    print(f"Result: {result}")

    print("\n📌 Scenario 3: Resume with missing case")
    print("-" * 80)
    result = await intake_resume("case-orphan-888")
    print(f"Result: {result}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✅ The decorator protects ALL intake handlers")
    print("✅ Auto-creates missing cases to prevent errors")
    print("✅ Preserves the original case_id during recovery")
    print("✅ Logs all recovery events for monitoring")
    print()
    print("Real implementation:")
    print("  - telegram_interface/handlers/intake_handlers.py:64-136")
    print("  - Applied to 5 handlers: intake_status, intake_cancel,")
    print("    intake_resume, handle_intake_callback, handle_text_message")
    print()


if __name__ == "__main__":
    asyncio.run(demo())
