"""add member type and company

Revision ID: f25b7a9430d1
Revises: e8d5b7a2c419
Create Date: 2026-09-18 19:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f25b7a9430d1"
down_revision: Union[str, Sequence[str], None] = "e8d5b7a2c419"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "student_profiles",
        sa.Column("member_type", sa.String(length=32), server_default="current_student", nullable=False),
    )
    op.add_column("student_profiles", sa.Column("company", sa.String(length=200), nullable=True))
    op.create_check_constraint(
        "ck_student_profiles_member_type",
        "student_profiles",
        "member_type IN ('current_student', 'alumni')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_student_profiles_member_type", "student_profiles", type_="check")
    op.drop_column("student_profiles", "company")
    op.drop_column("student_profiles", "member_type")
