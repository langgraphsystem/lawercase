"""Add case_id column to semantic_memory table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-20 00:00:00

Adds:
- case_id column to semantic_memory for linking documents to cases
- Index on case_id for efficient case-specific queries
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add case_id column to semantic_memory."""
    # Add case_id column
    op.add_column(
        "semantic_memory",
        sa.Column("case_id", sa.String(255), nullable=True),
        schema="mega_agent",
    )

    # Create index for case_id
    op.create_index(
        "idx_semantic_case_id",
        "semantic_memory",
        ["case_id"],
        schema="mega_agent",
    )


def downgrade() -> None:
    """Remove case_id column from semantic_memory."""
    op.drop_index("idx_semantic_case_id", table_name="semantic_memory", schema="mega_agent")
    op.drop_column("semantic_memory", "case_id", schema="mega_agent")
