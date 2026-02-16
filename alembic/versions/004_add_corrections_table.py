"""Add corrections table for user edits on predictions.

Revision ID: 004
Revises: 003
Create Date: 2026-02-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create corrections table
    op.create_table(
        "corrections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(20), nullable=False),
        sa.Column("box", sa.JSON(), nullable=True),
        sa.Column("original_box", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_corrections_prediction_id", "corrections", ["prediction_id"])


def downgrade() -> None:
    # Drop corrections table
    op.drop_index("ix_corrections_prediction_id", table_name="corrections")
    op.drop_table("corrections")
