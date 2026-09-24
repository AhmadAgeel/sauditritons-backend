from datetime import datetime

from sqlalchemy import (
    DateTime, 
    ForeignKey, 
    Index, 
    Integer,
    JSON,
    String, 
    Text,
    func, 
    CheckConstraint,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable = False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="member", server_default="member", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    activity_recency_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user",
        # cascade="all, delete-orphan",
        # single_parent=True,
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint(
            "degree IN ('BS', 'BA', 'MS', 'MA', 'PhD')",
            name="ck_student_profiles_degree",
        ),
        CheckConstraint(
            "board_membership_status IN ('current', 'former', 'never')",
            name="ck_student_profiles_board_membership_status",
        ),
        CheckConstraint(
            "member_type IN ('current_student', 'alumni')",
            name="ck_student_profiles_member_type",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    major: Mapped[str] = mapped_column(nullable=False)
    second_major: Mapped[str | None] = mapped_column(nullable=True)

    degree: Mapped[str] = mapped_column(nullable=False)

    minor: Mapped[str | None] = mapped_column(nullable=True)
    second_minor: Mapped[str | None] = mapped_column(nullable=True)

    graduation_year: Mapped[int] = mapped_column(nullable=False)
    member_type: Mapped[str] = mapped_column(
        String(32),
        default="current_student",
        server_default="current_student",
        nullable=False,
    )
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)

    bio: Mapped[str | None] = mapped_column(nullable=True)

    linkedin_url: Mapped[str | None] = mapped_column(nullable=True)
    github_url: Mapped[str | None] = mapped_column(nullable=True)
    profile_photo_url: Mapped[str | None] = mapped_column(nullable=True)

    is_visible: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    board_membership_status: Mapped[str] = mapped_column(
        server_default="never",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="student_profile")


class WhatsAppTicket(Base):
    __tablename__ = "whatsapp_tickets"
    __table_args__ = (
        Index(
            "ix_whatsapp_tickets_user_id_created_at",
            "user_id",
            "created_at",
        ),
    )

    token: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    invite: Mapped["WhatsAppInvite | None"] = relationship()
    user: Mapped["User"] = relationship()


class WhatsAppInvite(Base):
    __tablename__ = "whatsapp_invites"

    wa_inv_link: Mapped[str] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(
        ForeignKey("whatsapp_tickets.token", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    user: Mapped["User"] = relationship(
        secondary="whatsapp_tickets",
        viewonly=True,
    )
    join: Mapped["WhatsAppJoin | None"] = relationship(
        primaryjoin=lambda: WhatsAppInvite.wa_inv_link
        == foreign(WhatsAppJoin.wa_inv_link),
        viewonly=True,
    )


class WhatsAppUser(Base):
    __tablename__ = "whatsapp_users"

    lid: Mapped[str] = mapped_column(primary_key=True)

    phone_number: Mapped[str | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class WhatsAppJoin(Base):
    __tablename__ = "whatsapp_joins"

    wa_inv_link: Mapped[str] = mapped_column(
        primary_key=True,
    )
    lid: Mapped[str] = mapped_column(
        ForeignKey("whatsapp_users.lid"),
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    wa_user: Mapped["WhatsAppUser"] = relationship()


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    location: Mapped[str | None] = mapped_column(nullable=True)
    location_url: Mapped[str | None] = mapped_column(nullable=True)
    category: Mapped[str] = mapped_column(String(80), default="Gathering", server_default="Gathering", nullable=False)
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rsvp_opens_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rsvp_closes_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    show_rsvp_deadline: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )

    is_published: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )

    requires_check_in: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )

    is_paid: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at",
            name="ck_events_ends_after_starts",
        ),
        CheckConstraint(
            "rsvp_opens_at IS NULL OR rsvp_closes_at > rsvp_opens_at",
            name="ck_events_rsvp_closes_after_opens",
        ),
    )


class EventRSVP(Base):
    __tablename__ = "event_rsvps"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    ticket_code: Mapped[str] = mapped_column(
        unique=True,
        nullable=False,
    )

    companion_names: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )

    has_paid: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship()
    user: Mapped["User"] = relationship()
    check_in: Mapped["EventCheckIn | None"] = relationship(
        back_populates="rsvp",
        primaryjoin="EventRSVP.ticket_code == foreign(EventCheckIn.ticket_code)",
    )


class GuestEventRSVP(Base):
    __tablename__ = "guest_event_rsvps"

    ticket_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    attendee_name: Mapped[str] = mapped_column(String(200), nullable=False)
    attendee_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    companion_names: Mapped[list] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    has_paid: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event: Mapped["Event"] = relationship()
    check_in: Mapped["EventCheckIn | None"] = relationship(
        primaryjoin="GuestEventRSVP.ticket_code == foreign(EventCheckIn.ticket_code)",
        viewonly=True,
        uselist=False,
    )

    __table_args__ = (
        Index("uq_guest_event_rsvp_email", "event_id", "attendee_email", unique=True),
    )


class EventWalkIn(Base):
    __tablename__ = "event_walk_ins"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    attendee_name: Mapped[str] = mapped_column(String(160), nullable=False)
    attendee_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    recorded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    has_paid: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkspaceUser(Base):
    __tablename__ = "workspace_users"

    workspace_user_id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(nullable=False)

    check_ins: Mapped[list["EventCheckIn"]] = relationship(
        back_populates="workspace_user",
    )


class EventCheckIn(Base):
    __tablename__ = "event_check_ins"

    ticket_code: Mapped[str] = mapped_column(
        primary_key=True,
    )

    workspace_user_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_users.workspace_user_id"),
        nullable=False,
    )

    method: Mapped[str] = mapped_column(
        nullable=False,
    )

    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    rsvp: Mapped["EventRSVP"] = relationship(
        back_populates="check_in",
        primaryjoin="foreign(EventCheckIn.ticket_code) == EventRSVP.ticket_code",
    )

    workspace_user: Mapped["WorkspaceUser"] = relationship(
        back_populates="check_ins",
    )

    __table_args__ = (
        CheckConstraint(
            "method IN ('qr', 'manual')",
            name="ck_event_check_ins_method",
        ),
    )


class MagicLink(Base):
    __tablename__ = "magic_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        index=True, 
        nullable=False
    )
    token_hash: Mapped[str] = mapped_column(
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        unique=True,
        index=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    link_href: Mapped[str | None] = mapped_column(nullable=True)
    is_published: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="official_site", server_default="official_site", nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    href: Mapped[str] = mapped_column(nullable=False)
    featured: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    is_published: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BoardMember(Base):
    __tablename__ = "board_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(160), nullable=False)
    group_name: Mapped[str] = mapped_column(String(32), default="board", server_default="board", nullable=False)
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    is_published: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    actor: Mapped["User"] = relationship()






























