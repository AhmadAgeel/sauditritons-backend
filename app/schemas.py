from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Any, Literal
from urllib.parse import urlsplit


Degree = Literal["BS", "BA", "MS", "MA", "PhD"]
BoardMembershipStatus = Literal["current", "former", "never"]
MemberType = Literal["current_student", "alumni"]
CheckInMethod = Literal["qr", "manual"]


def safe_public_url(value: str | None, *, allow_relative: bool = False, allow_data_image: bool = False):
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if allow_relative and normalized.startswith("/") and not normalized.startswith("//"):
        return normalized
    if allow_data_image and normalized.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
        if len(normalized) > 2_750_000:
            raise ValueError("Image data is too large")
        return normalized
    parsed = urlsplit(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Public links must use a complete https URL")
    if len(normalized) > 2048:
        raise ValueError("Public link is too long")
    return normalized


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: Literal["member", "content_editor", "officer", "admin"]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AccountDeletionRequest(BaseModel):
    confirm_email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: str | None = None


class ActivityRecencyResponse(BaseModel):
    activity_recency_at: datetime
    next_update_at: datetime


class StudentProfileCreate(BaseModel):
    degree: Degree
    major: str
    graduation_year: int
    is_visible: bool
    member_type: MemberType = "current_student"
    company: str | None = Field(default=None, max_length=200)

    second_major: str | None = None
    minor: str | None = None
    second_minor: str | None = None
    
    linkedin_url: str | None = None
    github_url: str | None = None

    bio: str | None = None
    profile_photo_url: str | None = None

    @field_validator("linkedin_url", "github_url", "profile_photo_url")
    @classmethod
    def validate_public_profile_url(cls, value: str | None):
        return safe_public_url(value)


class StudentProfileUser(BaseModel):
    first_name: str
    last_name: str


class StudentProfileResponse(StudentProfileCreate):
    user_id: int
    is_approved: bool
    created_at: datetime
    user: StudentProfileUser
    board_membership_status: BoardMembershipStatus


class StudentProfileUpdate(BaseModel):
    degree: Degree | None = None
    major: str | None = None
    graduation_year: int | None = None
    member_type: MemberType | None = None
    company: str | None = Field(default=None, max_length=200)

    second_major: str | None = None
    minor: str | None = None
    second_minor: str | None = None

    linkedin_url: str | None = None
    github_url: str | None = None

    bio: str | None = None
    profile_photo_url: str | None = None

    is_visible: bool | None = None

    @field_validator("linkedin_url", "github_url", "profile_photo_url")
    @classmethod
    def validate_public_profile_url(cls, value: str | None):
        return safe_public_url(value)


class WhatsAppTicketResponse(BaseModel):
    token: str
    created_at: datetime


class WhatsAppInviterInfo(BaseModel):
    id: int
    first_name: str
    last_name: str


class WhatsAppInviteResponse(BaseModel):
    inviter: WhatsAppInviterInfo


class WhatsAppUserInfo(BaseModel):
    lid: str
    phone_number: str | None

    model_config = ConfigDict(from_attributes=True)


class WhatsAppJoinInfo(BaseModel):
    lid: str
    joined_at: datetime
    wa_user: WhatsAppUserInfo

    model_config = ConfigDict(from_attributes=True)


class WhatsAppTicketInviteInfo(BaseModel):
    wa_inv_link: str
    created_at: datetime
    join: WhatsAppJoinInfo | None

    model_config = ConfigDict(from_attributes=True)


class WhatsAppTicketInfo(BaseModel):
    token: str
    created_at: datetime
    invite: WhatsAppTicketInviteInfo | None

    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    location: str | None = None
    location_url: str | None = None
    category: str = "Gathering"
    image_url: str | None = None
    capacity: int | None = Field(default=None, ge=1)

    starts_at: datetime
    ends_at: datetime | None = None

    rsvp_opens_at: datetime | None = None
    rsvp_closes_at: datetime

    show_rsvp_deadline: bool = False
    is_paid: bool = False
    requires_check_in: bool = False
    is_published: bool = False

    @field_validator("location_url")
    @classmethod
    def validate_location_url(cls, value: str | None):
        return safe_public_url(value)

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None):
        return safe_public_url(value, allow_relative=True, allow_data_image=True)


class EventResponse(EventCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicEventResponse(EventResponse):
    remaining_seats: int | None
    registration_status: Literal["open", "full", "closed", "not_open"]


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    location: str | None = None
    location_url: str | None = None
    category: str | None = None
    image_url: str | None = None
    capacity: int | None = Field(default=None, ge=1)

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    rsvp_opens_at: datetime | None = None
    rsvp_closes_at: datetime | None = None

    show_rsvp_deadline: bool | None = None
    is_paid: bool | None = None
    requires_check_in: bool | None = None
    is_published: bool | None = None

    @field_validator("location_url")
    @classmethod
    def validate_location_url(cls, value: str | None):
        return safe_public_url(value)

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None):
        return safe_public_url(value, allow_relative=True, allow_data_image=True)


class EventRSVPCreate(BaseModel):
    companion_names: list[str] = Field(default_factory=list, max_length=3)


class EventRSVPResponse(BaseModel):
    event_id: int
    user_id: int
    ticket_code: str
    companion_names: list[str]
    has_paid: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuestEventRSVPCreate(BaseModel):
    attendee_name: str = Field(min_length=1, max_length=160)
    attendee_email: EmailStr
    companion_names: list[str] = Field(default_factory=list, max_length=3)
    answers: dict[str, Any] = Field(default_factory=dict)
    turnstile_token: str | None = Field(default=None, min_length=1, max_length=2048)


class GuestEventRSVPResponse(BaseModel):
    event_id: int
    ticket_code: str
    attendee_name: str
    attendee_email: EmailStr
    companion_names: list[str]
    has_paid: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventSummary(BaseModel):
    id: int
    title: str
    location: str | None
    location_url: str | None
    starts_at: datetime
    ends_at: datetime | None
    requires_check_in: bool

    model_config = ConfigDict(from_attributes=True)


class MyEventRSVPResponse(BaseModel):
    event_id: int
    ticket_code: str
    companion_names: list[str]
    has_paid: bool
    created_at: datetime
    event: EventSummary

    model_config = ConfigDict(from_attributes=True)


class PublicTicketScanner(BaseModel):
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class PublicTicketCheckIn(BaseModel):
    checked_in_at: datetime
    workspace_user: PublicTicketScanner

    model_config = ConfigDict(from_attributes=True)


class EventRSVPUser(BaseModel):
    id: int
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)


class PublicTicketResponse(BaseModel):
    ticket_code: str
    event: EventSummary
    user: EventRSVPUser | None = None
    attendee_name: str | None = None
    companion_names: list[str]
    check_in: PublicTicketCheckIn | None

    model_config = ConfigDict(from_attributes=True)


class EventCheckInCreate(BaseModel):
    ticket_code: str
    workspace_user_id: int
    method: CheckInMethod
    mark_paid: bool = False


class EventCheckInResponse(BaseModel):
    status: Literal["checked_in", "payment_required"]
    ticket_code: str
    has_paid: bool


class WorkspaceUserUpsert(BaseModel):
    display_name: str


class WorkspaceUserResponse(BaseModel):
    workspace_user_id: int
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class EventCheckInInfo(BaseModel):
    method: CheckInMethod
    checked_in_at: datetime
    workspace_user: WorkspaceUserResponse

    model_config = ConfigDict(from_attributes=True)


class InternalEventRSVPResponse(BaseModel):
    user_id: int
    ticket_code: str
    has_paid: bool
    created_at: datetime

    user: EventRSVPUser
    check_in: EventCheckInInfo | None

    model_config = ConfigDict(from_attributes=True)


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkVerify(BaseModel):
    token: str


class CompleteSignup(BaseModel):
    token: str
    first_name: str
    last_name: str
    password: str | None = None


class MagicLinkVerifyResponse(BaseModel):
    signup_required: bool
    auth: Token | None = None


class TicketCheckInEvent(BaseModel):
    checked_in_at: datetime
    scanned_by: str


UserRole = Literal["member", "content_editor", "officer", "admin"]


class AdminUserResponse(UserResponse):
    student_profile: StudentProfileResponse | None = None


class UserRoleUpdate(BaseModel):
    role: UserRole


class ProfileModerationUpdate(BaseModel):
    is_approved: bool | None = None
    board_membership_status: BoardMembershipStatus | None = None


class AnnouncementCreate(BaseModel):
    title: str
    body: str
    link_label: str | None = None
    link_href: str | None = None
    is_published: bool = False
    is_pinned: bool = False

    @field_validator("link_href")
    @classmethod
    def validate_link_href(cls, value: str | None):
        return safe_public_url(value, allow_relative=True)


class AnnouncementUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    link_label: str | None = None
    link_href: str | None = None
    is_published: bool | None = None
    is_pinned: bool | None = None

    @field_validator("link_href")
    @classmethod
    def validate_link_href(cls, value: str | None):
        return safe_public_url(value, allow_relative=True)


class AnnouncementResponse(AnnouncementCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ResourceCreate(BaseModel):
    title: str
    description: str
    category: str
    kind: Literal["pdf", "official_site"] = "official_site"
    source: str
    href: str
    featured: bool = False
    is_published: bool = False

    @field_validator("href")
    @classmethod
    def validate_href(cls, value: str):
        validated = safe_public_url(value, allow_relative=True)
        if validated is None:
            raise ValueError("Resource link is required")
        return validated


class ResourceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    kind: Literal["pdf", "official_site"] | None = None
    source: str | None = None
    href: str | None = None
    featured: bool | None = None
    is_published: bool | None = None

    @field_validator("href")
    @classmethod
    def validate_href(cls, value: str | None):
        return safe_public_url(value, allow_relative=True)


class ResourceResponse(ResourceCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BoardMemberCreate(BaseModel):
    name: str
    role: str
    group_name: Literal["executive", "board"] = "board"
    image_url: str | None = None
    linkedin_url: str | None = None
    email: EmailStr | None = None
    sort_order: int = 0
    is_published: bool = True

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None):
        return safe_public_url(value, allow_relative=True, allow_data_image=True)

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None):
        return safe_public_url(value)


class BoardMemberUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    group_name: Literal["executive", "board"] | None = None
    image_url: str | None = None
    linkedin_url: str | None = None
    email: EmailStr | None = None
    sort_order: int | None = None
    is_published: bool | None = None

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None):
        return safe_public_url(value, allow_relative=True, allow_data_image=True)

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None):
        return safe_public_url(value)


class BoardMemberResponse(BoardMemberCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: int
    action: str
    target_type: str
    target_id: str
    details: dict[str, Any]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminRsvpResponse(BaseModel):
    ticket_code: str
    attendee_name: str
    attendee_email: str | None
    companion_count: int
    has_paid: bool
    checked_in_at: datetime | None
    created_at: datetime


class AdminAttendeeResponse(BaseModel):
    id: str
    source: Literal["member", "guest", "walk_in"]
    ticket_code: str | None
    attendee_name: str
    attendee_email: str | None
    companion_names: list[str]
    companion_count: int
    has_paid: bool
    registered_at: datetime
    checked_in_at: datetime | None


class EventWalkInCreate(BaseModel):
    attendee_name: str = Field(min_length=1, max_length=160)
    attendee_email: EmailStr | None = None
    mark_paid: bool = False


class EventWalkInResponse(BaseModel):
    id: int
    event_id: int
    attendee_name: str
    attendee_email: str | None
    has_paid: bool
    created_at: datetime
    checked_in_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminCheckInCreate(BaseModel):
    mark_paid: bool = False
