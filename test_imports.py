"""
Simple import test to verify all code is syntactically correct
and can be imported without errors.
"""

from __future__ import annotations

import sys


def test_imports():
    """Test that all modified files can be imported."""
    print("=" * 80)
    print("TESTING IMPORTS")
    print("=" * 80)
    print()

    errors = []

    # Test 1: Import intake handlers
    print("1. Testing telegram_interface.handlers.intake_handlers...")
    try:
        from telegram_interface.handlers import intake_handlers

        print("   ✅ Successfully imported intake_handlers")

        # Check that decorator exists
        assert hasattr(
            intake_handlers, "ensure_case_exists"
        ), "Missing ensure_case_exists decorator"
        print("   ✅ ensure_case_exists decorator found")

        # Check that decorated functions exist
        assert hasattr(intake_handlers, "intake_start"), "Missing intake_start"
        assert hasattr(intake_handlers, "intake_status"), "Missing intake_status"
        assert hasattr(intake_handlers, "intake_cancel"), "Missing intake_cancel"
        assert hasattr(intake_handlers, "intake_resume"), "Missing intake_resume"
        print("   ✅ All intake handlers found")

    except Exception as e:
        errors.append(f"intake_handlers: {e!s}")
        print(f"   ❌ Error: {e!s}")

    print()

    # Test 2: Check recovery script structure
    print("2. Testing recovery script structure...")
    try:
        with open("recover_orphaned_intake_cases.py", encoding="utf-8") as f:
            content = f.read()

        # Check for key functions
        assert "find_orphaned_intake_records" in content, "Missing find_orphaned_intake_records"
        assert "recover_orphaned_case" in content, "Missing recover_orphaned_case"
        assert "async def main" in content, "Missing main function"
        assert "--dry-run" in content, "Missing dry-run support"
        print("   ✅ All key functions present in recovery script")

    except Exception as e:
        errors.append(f"recovery_script: {e!s}")
        print(f"   ❌ Error: {e!s}")

    print()

    # Test 3: Check test file structure
    print("3. Testing test file structure...")
    try:
        with open("tests/integration/telegram/test_intake_flow.py", encoding="utf-8") as f:
            content = f.read()

        # Check for key test classes
        assert "TestIntakeStartAtomicity" in content, "Missing TestIntakeStartAtomicity"
        assert "TestEnsureCaseExistsDecorator" in content, "Missing TestEnsureCaseExistsDecorator"
        assert "TestOrphanPrevention" in content, "Missing TestOrphanPrevention"
        assert "TestDataRecovery" in content, "Missing TestDataRecovery"
        assert "test_full_intake_flow_end_to_end" in content, "Missing end-to-end test"
        print("   ✅ All test classes and functions present")

    except Exception as e:
        errors.append(f"test_file: {e!s}")
        print(f"   ❌ Error: {e!s}")

    print()

    # Test 4: Check documentation files
    print("4. Checking documentation files...")
    try:
        docs = ["INTAKE_BUG_FIX_DOCUMENTATION.md", "INTAKE_BUG_FIX_SUMMARY.md", "PR_DESCRIPTION.md"]

        for doc in docs:
            with open(doc, encoding="utf-8") as f:
                content = f.read()
            assert len(content) > 100, f"{doc} seems empty or too short"
            print(f"   ✅ {doc} exists and has content")

    except Exception as e:
        errors.append(f"documentation: {e!s}")
        print(f"   ❌ Error: {e!s}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if errors:
        print(f"❌ {len(errors)} error(s) found:")
        for error in errors:
            print(f"   - {error}")
        return 1

    print("✅ All imports and structure checks passed!")
    print()
    print("Note: Integration tests require database connection.")
    print("Run with active PostgreSQL database:")
    print("  pytest tests/integration/telegram/test_intake_flow.py -v")
    print()
    print("Recovery script requires database connection:")
    print("  python recover_orphaned_intake_cases.py --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(test_imports())
