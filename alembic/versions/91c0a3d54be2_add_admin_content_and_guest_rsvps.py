"""add admin content and guest RSVPs

Revision ID: 91c0a3d54be2
Revises: 20b3b5688fcb
Create Date: 2026-09-08 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "91c0a3d54be2"
down_revision: Union[str, Sequence[str], None] = "20b3b5688fcb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=32), server_default="member", nullable=False))
    op.create_check_constraint("ck_users_role", "users", "role IN ('member', 'content_editor', 'officer', 'admin')")
    op.add_column("events", sa.Column("category", sa.String(length=80), server_default="Gathering", nullable=False))
    op.add_column("events", sa.Column("image_url", sa.String(), nullable=True))
    op.add_column("events", sa.Column("capacity", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_events_capacity_positive", "events", "capacity IS NULL OR capacity > 0")

    op.drop_constraint("event_check_ins_ticket_code_fkey", "event_check_ins", type_="foreignkey")
    op.create_table(
        "guest_event_rsvps",
        sa.Column("ticket_code", sa.String(length=32), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("attendee_name", sa.String(length=200), nullable=False),
        sa.Column("attendee_email", sa.String(length=320), nullable=False),
        sa.Column("companion_names", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("answers", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("has_paid", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ticket_code"),
    )
    op.create_index("ix_guest_event_rsvps_event_id", "guest_event_rsvps", ["event_id"])
    op.create_index("ix_guest_event_rsvps_attendee_email", "guest_event_rsvps", ["attendee_email"])
    op.create_index("uq_guest_event_rsvp_email", "guest_event_rsvps", ["event_id", "attendee_email"], unique=True)

    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False), sa.Column("link_label", sa.String(length=120)), sa.Column("link_href", sa.String()),
        sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False), sa.Column("is_pinned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(length=240), nullable=False), sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False), sa.Column("kind", sa.String(length=32), server_default="official_site", nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False), sa.Column("href", sa.String(), nullable=False),
        sa.Column("featured", sa.Boolean(), server_default="false", nullable=False), sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind IN ('pdf', 'official_site')", name="ck_resources_kind"),
    )
    op.create_table(
        "board_members",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=200), nullable=False), sa.Column("role", sa.String(length=160), nullable=False),
        sa.Column("group_name", sa.String(length=32), server_default="board", nullable=False), sa.Column("image_url", sa.String()), sa.Column("linkedin_url", sa.String()),
        sa.Column("email", sa.String(length=320)), sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default="true", nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("group_name IN ('executive', 'board')", name="ck_board_members_group"),
    )
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False), sa.Column("target_type", sa.String(length=80), nullable=False), sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("details", sa.JSON(), server_default="{}", nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("admin_audit_log"); op.drop_table("board_members"); op.drop_table("resources"); op.drop_table("announcements")
    op.drop_index("uq_guest_event_rsvp_email", table_name="guest_event_rsvps")
    op.drop_index("ix_guest_event_rsvps_attendee_email", table_name="guest_event_rsvps")
    op.drop_index("ix_guest_event_rsvps_event_id", table_name="guest_event_rsvps")
    op.drop_table("guest_event_rsvps")
    op.create_foreign_key("event_check_ins_ticket_code_fkey", "event_check_ins", "event_rsvps", ["ticket_code"], ["ticket_code"], ondelete="CASCADE")
    op.drop_constraint("ck_events_capacity_positive", "events", type_="check")
    op.drop_column("events", "capacity"); op.drop_column("events", "image_url"); op.drop_column("events", "category")
    op.drop_constraint("ck_users_role", "users", type_="check"); op.drop_column("users", "role")
