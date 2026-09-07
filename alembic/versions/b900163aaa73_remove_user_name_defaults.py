"""remove user name defaults

Revision ID: b900163aaa73
Revises: 3755a16f5008
Create Date: 2026-08-27 23:51:35.067501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b900163aaa73'
down_revision: Union[str, Sequence[str], None] = '3755a16f5008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("users", "first_name", server_default=None)
    op.alter_column("users", "last_name", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("users", "first_name", server_default="")
    op.alter_column("users", "last_name", server_default="")
