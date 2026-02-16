"""Initial schema for predictions and feedback tables.

Revision ID: 001
Revises: None
Create Date: 2025-01-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create predictions table
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("image_hash", sa.String(64), nullable=False),
        sa.Column("colony_count", sa.Integer(), nullable=False),
        sa.Column("confidence_threshold", sa.Float(), nullable=False),
        sa.Column("model_used", sa.String(50), nullable=False),
        sa.Column("original_image_key", sa.String(255), nullable=False),
        sa.Column("annotated_image_key", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_image_hash", "predictions", ["image_hash"])

    # Create feedback table
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("actual_count", sa.Integer(), nullable=False),
        sa.Column("comments", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["prediction_id"], ["predictions.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_feedback_prediction_id", "feedback", ["prediction_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_prediction_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_predictions_image_hash", table_name="predictions")
    op.drop_table("predictions")
