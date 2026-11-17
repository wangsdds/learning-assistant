"""text questions and model grading

Revision ID: d4f1a9c2e870
Revises: b7c4f0a2d901
Create Date: 2026-11-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f1a9c2e870"
down_revision: Union[str, Sequence[str], None] = "b7c4f0a2d901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("question") as batch_op:
        batch_op.alter_column(
            "system_answer",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "question_type",
                sa.String(length=16),
                nullable=False,
                server_default="numeric",
            )
        )
        batch_op.add_column(sa.Column("reference_answer", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("rubric", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("difficulty", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("source_chunk_ids", sa.Text(), nullable=True))

    with op.batch_alter_table("answer") as batch_op:
        batch_op.add_column(sa.Column("feedback", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("rubric_hits", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("rubric_misses", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("grade_model", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("answer") as batch_op:
        batch_op.drop_column("grade_model")
        batch_op.drop_column("rubric_misses")
        batch_op.drop_column("rubric_hits")
        batch_op.drop_column("feedback")

    with op.batch_alter_table("question") as batch_op:
        batch_op.drop_column("source_chunk_ids")
        batch_op.drop_column("difficulty")
        batch_op.drop_column("rubric")
        batch_op.drop_column("reference_answer")
        batch_op.drop_column("question_type")
        batch_op.alter_column(
            "system_answer",
            existing_type=sa.Integer(),
            nullable=False,
        )
