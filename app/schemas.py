from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Literal


Degree = Literal["BS", "BA", "MS", "MA", "PhD"]
BoardMembershipStatus = Literal["current", "former", "never"]
CheckInMethod = Literal["qr", "manual"]


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
    created_at: datetime


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

    second_major: str | None = None
    minor: str | None = None
    second_minor: str | None = None
    
    linkedin_url: str | None = None
    github_url: str | None = None

    bio: str | None = None
    profile_photo_url: str | None = None


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

    second_major: str | None = None
    minor: str | None = None
    second_minor: str | None = None

    linkedin_url: str | None = None
    github_url: str | None = None

    bio: str | None = None
    profile_photo_url: str | None = None

    is_visible: bool | None = None


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
    title: str
    description: str | None = None
    location: str | None = None

    starts_at: datetime
    ends_at: datetime | None = None

    rsvp_opens_at: datetime | None = None
    rsvp_closes_at: datetime

    show_rsvp_deadline: bool = False
    is_paid: bool = False
    requires_check_in: bool = False
    is_published: bool = False


class EventResponse(EventCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    rsvp_opens_at: datetime | None = None
    rsvp_closes_at: datetime | None = None

    show_rsvp_deadline: bool | None = None
    is_paid: bool | None = None
    requires_check_in: bool | None = None
    is_published: bool | None = None


class EventRSVPResponse(BaseModel):
    event_id: int
    user_id: int
    ticket_code: str
    has_paid: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventSummary(BaseModel):
    id: int
    title: str
    location: str | None
    starts_at: datetime
    ends_at: datetime | None
    requires_check_in: bool

    model_config = ConfigDict(from_attributes=True)


class MyEventRSVPResponse(BaseModel):
    event_id: int
    ticket_code: str
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
    user: EventRSVPUser
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







