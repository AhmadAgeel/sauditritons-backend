"""add event RSVP deadline visibility

Revision ID: 20b3b5688fcb
Revises: 949e02081805
Create Date: 2026-09-08 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20b3b5688fcb"
down_revision: Union[str, Sequence[str], None] = "949e02081805"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "show_rsvp_deadline",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "show_rsvp_deadline")
