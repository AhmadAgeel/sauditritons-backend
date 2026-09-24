"""record ticket-free walk-ins admitted by event staff

Revision ID: 20260924walkins
Revises: 20260920board
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260924walkins"
down_revision: Union[str, Sequence[str], None] = "20260920board"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_walk_ins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attendee_name", sa.String(length=160), nullable=False),
        sa.Column("attendee_email", sa.String(length=320), nullable=True),
        sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("has_paid", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_event_walk_ins_event_id", "event_walk_ins", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_event_walk_ins_event_id", table_name="event_walk_ins")
    op.drop_table("event_walk_ins")
