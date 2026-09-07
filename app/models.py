from datetime import datetime

from sqlalchemy import (
    DateTime, 
    ForeignKey, 
    Index, 
    String, 
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
    )


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
        ForeignKey(
            "event_rsvps.ticket_code",
            ondelete="CASCADE",
        ),
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



































