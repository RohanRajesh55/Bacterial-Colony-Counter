"""Add user_id to predictions and create api_keys table.

Revision ID: 003
Revises: 002
Create Date: 2025-01-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to predictions table (nullable for backward compatibility)
    op.add_column(
        "predictions",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_predictions_user_id", "predictions", ["user_id"])

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])


def downgrade() -> None:
    # Drop api_keys table
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")

    # Remove user_id column from predictions
    op.drop_index("ix_predictions_user_id", table_name="predictions")
    op.drop_column("predictions", "user_id")
