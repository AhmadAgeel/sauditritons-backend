"""add event maps and member guests

Revision ID: e8d5b7a2c419
Revises: c3a92f41d801
Create Date: 2026-09-18 16:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8d5b7a2c419"
down_revision: Union[str, Sequence[str], None] = "c3a92f41d801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("location_url", sa.String(), nullable=True))
    op.add_column(
        "event_rsvps",
        sa.Column("companion_names", sa.JSON(), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("event_rsvps", "companion_names")
    op.drop_column("events", "location_url")
