"""unpublish the 2025-26 board while the 2026-27 board is selected

Revision ID: 20260920board
Revises: f25b7a9430d1
Create Date: 2026-09-20 04:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260920board"
down_revision: Union[str, Sequence[str], None] = "f25b7a9430d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE board_members SET is_published = false WHERE is_published = true")


def downgrade() -> None:
    # Publication is editorial state. Do not republish people automatically.
    pass
