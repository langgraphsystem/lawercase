"""
Storage module for case intake progress tracking.

Provides CRUD operations for the case_intake_progress table, which stores
the state of multi-block intake questionnaires per user and case.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, CheckConstraint, Index, Integer, String, select, update
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.storage.connection import get_db_manager


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy models."""


class CaseIntakeProgressDB(Base):
    """
    SQLAlchemy model for case_intake_progress table.

    Tracks progress through intake questionnaire blocks and questions.
    """

    __tablename__ = "case_intake_progress"
    __table_args__ = (
        CheckConstraint("length(user_id) > 0", name="intake_user_id_not_empty"),
        CheckConstraint("length(case_id) > 0", name="intake_case_id_not_empty"),
        CheckConstraint("length(current_block) > 0", name="intake_current_block_not_empty"),
        CheckConstraint("current_step >= 0", name="intake_current_step_non_negative"),
        Index("idx_case_intake_user", "user_id"),
        Index("idx_case_intake_case", "case_id"),
        Index("idx_case_intake_updated", "updated_at", postgresql_using="btree"),
        {"schema": "mega_agent"},
    )

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=False)
    case_id: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=False)
    current_block: Mapped[str] = mapped_column(String(100), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_blocks: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CaseIntakeProgress:
    """
    Pydantic-like data class for intake progress (for external API).
    """

    def __init__(
        self,
        user_id: str,
        case_id: str,
        current_block: str,
        current_step: int = 0,
        completed_blocks: list[str] | None = None,
        updated_at: datetime | None = None,
    ):
        self.user_id = user_id
        self.case_id = case_id
        self.current_block = current_block
        self.current_step = current_step
        self.completed_blocks = completed_blocks or []
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "case_id": self.case_id,
            "current_block": self.current_block,
            "current_step": self.current_step,
            "completed_blocks": self.completed_blocks,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_db(cls, db_row: CaseIntakeProgressDB) -> "CaseIntakeProgress":
        """Convert database model to CaseIntakeProgress object."""
        return cls(
            user_id=db_row.user_id,
            case_id=db_row.case_id,
            current_block=db_row.current_block,
            current_step=db_row.current_step,
            completed_blocks=db_row.completed_blocks,
            updated_at=db_row.updated_at,
        )


# -------------------- CRUD OPERATIONS --------------------


async def get_progress(user_id: str, case_id: str) -> CaseIntakeProgress | None:
    """
    Retrieve intake progress for a specific user and case.

    Args:
        user_id: User identifier
        case_id: Case UUID

    Returns:
        CaseIntakeProgress object if found, None otherwise
    """
    db = get_db_manager()

    async with db.session() as session:
        stmt = select(CaseIntakeProgressDB).where(
            CaseIntakeProgressDB.user_id == user_id, CaseIntakeProgressDB.case_id == case_id
        )
        result = await session.execute(stmt)
        db_row = result.scalar_one_or_none()

        if db_row is None:
            return None

        return CaseIntakeProgress.from_db(db_row)


async def set_progress(
    user_id: str,
    case_id: str,
    current_block: str,
    current_step: int,
    completed_blocks: list[str],
) -> None:
    """
    Create or update intake progress for a user and case.

    This operation is atomic - uses INSERT ON CONFLICT to ensure no race conditions.

    Args:
        user_id: User identifier
        case_id: Case UUID
        current_block: ID of the current block being processed
        current_step: Index of the next question within current_block (0-based)
        completed_blocks: List of block IDs that have been fully completed
    """
    db = get_db_manager()

    async with db.session() as session:
        # Use INSERT ON CONFLICT to handle both create and update atomically
        stmt = """
        INSERT INTO mega_agent.case_intake_progress (
            user_id, case_id, current_block, current_step, completed_blocks, updated_at
        ) VALUES (
            :user_id, :case_id, :current_block, :current_step, :completed_blocks, NOW()
        )
        ON CONFLICT (user_id, case_id)
        DO UPDATE SET
            current_block = EXCLUDED.current_block,
            current_step = EXCLUDED.current_step,
            completed_blocks = EXCLUDED.completed_blocks,
            updated_at = NOW()
        """

        await session.execute(
            stmt,
            {
                "user_id": user_id,
                "case_id": case_id,
                "current_block": current_block,
                "current_step": current_step,
                "completed_blocks": completed_blocks,
            },
        )
        await session.commit()


async def reset_progress(user_id: str, case_id: str) -> None:
    """
    Delete intake progress for a user and case (used for restarting intake).

    Args:
        user_id: User identifier
        case_id: Case UUID
    """
    db = get_db_manager()

    async with db.session() as session:
        stmt = select(CaseIntakeProgressDB).where(
            CaseIntakeProgressDB.user_id == user_id, CaseIntakeProgressDB.case_id == case_id
        )
        result = await session.execute(stmt)
        db_row = result.scalar_one_or_none()

        if db_row is not None:
            await session.delete(db_row)
            await session.commit()


async def advance_step(user_id: str, case_id: str) -> CaseIntakeProgress | None:
    """
    Increment current_step by 1 (convenience method for moving to next question).

    Args:
        user_id: User identifier
        case_id: Case UUID

    Returns:
        Updated CaseIntakeProgress object, or None if not found
    """
    db = get_db_manager()

    async with db.session() as session:
        stmt = (
            update(CaseIntakeProgressDB)
            .where(
                CaseIntakeProgressDB.user_id == user_id, CaseIntakeProgressDB.case_id == case_id
            )
            .values(current_step=CaseIntakeProgressDB.current_step + 1, updated_at=datetime.utcnow())
            .returning(CaseIntakeProgressDB)
        )

        result = await session.execute(stmt)
        await session.commit()
        db_row = result.scalar_one_or_none()

        if db_row is None:
            return None

        return CaseIntakeProgress.from_db(db_row)


async def complete_block(user_id: str, case_id: str, block_id: str, next_block: str) -> None:
    """
    Mark a block as completed and move to the next block.

    Args:
        user_id: User identifier
        case_id: Case UUID
        block_id: ID of the block that was just completed
        next_block: ID of the next block to start
    """
    progress = await get_progress(user_id, case_id)

    if progress is None:
        # Create new progress starting at next block
        await set_progress(
            user_id=user_id,
            case_id=case_id,
            current_block=next_block,
            current_step=0,
            completed_blocks=[block_id],
        )
    else:
        # Update existing progress
        if block_id not in progress.completed_blocks:
            progress.completed_blocks.append(block_id)

        await set_progress(
            user_id=user_id,
            case_id=case_id,
            current_block=next_block,
            current_step=0,
            completed_blocks=progress.completed_blocks,
        )
