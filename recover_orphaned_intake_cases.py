"""
Data Recovery Script for Orphaned Intake Progress Records

This script finds and recovers orphaned case_intake_progress records
where intake progress exists but the corresponding case record is missing.

Problem:
    - case_intake_progress exists with a case_id
    - But mega_agent.cases table has no record with that case_id
    - Causes CaseNotFoundError when trying to access the case

Solution:
    - Find all orphaned intake progress records
    - Create matching case records for each orphaned record
    - Preserve the original case_id to maintain data integrity

Usage:
    python recover_orphaned_intake_cases.py [--dry-run]

Options:
    --dry-run    Show what would be recovered without making changes
"""

import asyncio
import sys
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select, text

from core.groupagents.case_agent import CaseAgent
from core.groupagents.models import CaseType
from core.storage.connection import get_db_manager
from core.storage.intake_progress import CaseIntakeProgressDB

logger = structlog.get_logger(__name__)


async def find_orphaned_intake_records():
    """
    Find all intake progress records without corresponding case records.

    Returns:
        List of tuples: [(user_id, case_id), ...]
    """
    db = get_db_manager()

    async with db.session() as session:
        # SQL query to find orphaned records
        query = text(
            """
            SELECT DISTINCT cip.user_id, cip.case_id
            FROM mega_agent.case_intake_progress cip
            WHERE NOT EXISTS (
                SELECT 1
                FROM mega_agent.cases c
                WHERE c.case_id::text = cip.case_id
            )
            ORDER BY cip.updated_at DESC
            """
        )

        result = await session.execute(query)
        orphans = result.fetchall()

        return [(row[0], row[1]) for row in orphans]


async def recover_orphaned_case(case_agent: CaseAgent, user_id: str, case_id: str, dry_run: bool = False):
    """
    Create a case record for an orphaned intake progress.

    Args:
        case_agent: CaseAgent instance
        user_id: User ID
        case_id: Case ID (UUID as string)
        dry_run: If True, only log what would be done without making changes

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        logger.info(
            "recovery.dry_run",
            user_id=user_id,
            case_id=case_id,
            action="would_create_case"
        )
        return True

    try:
        # Create case with the orphaned case_id
        case = await case_agent.acreate_case(
            user_id=user_id,
            case_data={
                "case_id": case_id,  # Preserve original case_id
                "title": "Intake Session (Recovered)",
                "description": f"Case automatically recovered on {datetime.utcnow().isoformat()}",
                "client_id": user_id,
                "case_type": CaseType.IMMIGRATION.value,
                "status": "draft",
            }
        )

        logger.info(
            "recovery.case_created",
            user_id=user_id,
            case_id=case_id,
            status="success"
        )
        return True

    except Exception as e:
        logger.error(
            "recovery.case_creation_failed",
            user_id=user_id,
            case_id=case_id,
            error=str(e),
            error_type=type(e).__name__
        )
        return False


async def main(dry_run: bool = False):
    """
    Main recovery process.

    Args:
        dry_run: If True, only show what would be recovered without making changes
    """
    print("=" * 80)
    print("ORPHANED INTAKE CASES RECOVERY SCRIPT")
    print("=" * 80)
    print()

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    # Initialize CaseAgent
    case_agent = CaseAgent()

    # Find orphaned records
    print("🔎 Searching for orphaned intake progress records...")
    orphans = await find_orphaned_intake_records()

    if not orphans:
        print("✅ No orphaned records found. Database is healthy!")
        return 0

    print(f"⚠️  Found {len(orphans)} orphaned intake progress record(s)")
    print()

    # Display orphaned records
    print("Orphaned Records:")
    print("-" * 80)
    for i, (user_id, case_id) in enumerate(orphans, 1):
        print(f"{i:3d}. User: {user_id:20s} | Case: {case_id}")
    print()

    if not dry_run:
        # Ask for confirmation
        response = input("Do you want to recover these cases? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("❌ Recovery cancelled by user")
            return 1
        print()

    # Recover each orphaned record
    print("🔧 Starting recovery process...")
    print()

    success_count = 0
    failure_count = 0

    for i, (user_id, case_id) in enumerate(orphans, 1):
        print(f"[{i}/{len(orphans)}] Processing: User {user_id}, Case {case_id}...")

        success = await recover_orphaned_case(case_agent, user_id, case_id, dry_run)

        if success:
            success_count += 1
            status = "✅ OK" if not dry_run else "✅ Would recover"
        else:
            failure_count += 1
            status = "❌ FAILED"

        print(f"         {status}")

    print()
    print("=" * 80)
    print("RECOVERY SUMMARY")
    print("=" * 80)
    print(f"Total orphaned records: {len(orphans)}")
    print(f"Successfully recovered: {success_count}")
    print(f"Failed: {failure_count}")

    if dry_run:
        print()
        print("This was a DRY RUN. Run without --dry-run to actually recover cases.")

    print()

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv

    # Run recovery
    exit_code = asyncio.run(main(dry_run))
    sys.exit(exit_code)
