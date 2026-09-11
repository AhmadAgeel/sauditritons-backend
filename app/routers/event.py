from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from app import models, schemas, oauth2
from app.database import get_db

from datetime import datetime, timezone
import secrets
import string


router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


def generate_ticket_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(
        secrets.choice(alphabet)
        for _ in range(12)
    )


def validate_registration(event: models.Event, db: Session, requested_seats: int = 1):
    now = datetime.now(timezone.utc)
    if event.rsvp_opens_at is not None and now < event.rsvp_opens_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RSVP has not opened yet")
    if now >= event.rsvp_closes_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RSVP has closed")
    if event.capacity is not None:
        members = db.scalar(select(func.count()).select_from(models.EventRSVP).where(models.EventRSVP.event_id == event.id)) or 0
        guest_groups = db.scalars(select(models.GuestEventRSVP.companion_names).where(models.GuestEventRSVP.event_id == event.id)).all()
        occupied = members + sum(1 + len(companions) for companions in guest_groups)
        if occupied + requested_seats > event.capacity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This event is full")


@router.get(
    "/",
    response_model=list[schemas.EventResponse],
)
def get_events(
    db: Session = Depends(get_db),
):
    stmt = (
        select(models.Event)
        .where(models.Event.is_published)
        .order_by(models.Event.starts_at)
    )

    return db.scalars(stmt).all()


@router.get(
    "/me/rsvps",
    response_model=list[schemas.MyEventRSVPResponse],
)
def get_my_rsvps(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(models.EventRSVP)
        .options(selectinload(models.EventRSVP.event))
        .where(models.EventRSVP.user_id == current_user.id)
        .order_by(models.EventRSVP.created_at.desc())
    )

    return db.scalars(stmt).all()


@router.get(
    "/{event_id}",
    response_model=schemas.EventResponse,
)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    event = db.get(models.Event, event_id)

    if event is None or not event.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event


@router.post(
    "/{event_id}/rsvp",
    response_model=schemas.EventRSVPResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rsvp(
    event_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    event = db.get(models.Event, event_id)

    if event is None or not event.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    existing_rsvp = db.get(
        models.EventRSVP,
        (event_id, current_user.id),
    )

    if existing_rsvp is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already RSVP'd",
        )

    validate_registration(event, db)

    rsvp = models.EventRSVP(
        event_id=event_id,
        user_id=current_user.id,
        ticket_code=generate_ticket_code(),
    )

    db.add(rsvp)
    db.commit()
    db.refresh(rsvp)

    return rsvp


@router.post(
    "/{event_id}/guest-rsvp",
    response_model=schemas.GuestEventRSVPResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_guest_rsvp(event_id: int, payload: schemas.GuestEventRSVPCreate, db: Session = Depends(get_db)):
    event = db.get(models.Event, event_id)
    if event is None or not event.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    attendee_email = str(payload.attendee_email).lower()
    if db.scalar(select(models.GuestEventRSVP.ticket_code).where(
        models.GuestEventRSVP.event_id == event_id,
        models.GuestEventRSVP.attendee_email == attendee_email,
    )) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email is already registered for the event")
    validate_registration(event, db, 1 + len(payload.companion_names))
    record = models.GuestEventRSVP(
        event_id=event_id,
        ticket_code=generate_ticket_code(),
        attendee_name=payload.attendee_name.strip(),
        attendee_email=attendee_email,
        companion_names=[name.strip() for name in payload.companion_names if name.strip()],
        answers=payload.answers,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email is already registered for the event")
    db.refresh(record)
    return record


@router.delete("/{event_id}/guest-rsvp", status_code=status.HTTP_204_NO_CONTENT)
def cancel_guest_rsvp(event_id: int, email: str, ticket_code: str, db: Session = Depends(get_db)):
    record = db.scalar(select(models.GuestEventRSVP).where(
        models.GuestEventRSVP.event_id == event_id,
        models.GuestEventRSVP.attendee_email == email.lower(),
        models.GuestEventRSVP.ticket_code == ticket_code.replace("-", "").upper(),
    ))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    if record.check_in is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot cancel after check-in")
    db.delete(record); db.commit()


@router.delete(
    "/{event_id}/rsvp",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_rsvp(
    event_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    rsvp = db.get(
        models.EventRSVP,
        (event_id, current_user.id),
    )

    if rsvp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RSVP not found",
        )

    db.delete(rsvp)
    db.commit()
