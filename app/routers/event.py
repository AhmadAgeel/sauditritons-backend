from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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

    now = datetime.now(timezone.utc)

    if event.rsvp_opens_at is not None and now < event.rsvp_opens_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RSVP has not opened yet",
        )

    if now >= event.rsvp_closes_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RSVP has closed",
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

    rsvp = models.EventRSVP(
        event_id=event_id,
        user_id=current_user.id,
        ticket_code=generate_ticket_code(),
    )

    db.add(rsvp)
    db.commit()
    db.refresh(rsvp)

    return rsvp


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


@router.delete(
    "/{event_id}/rsvp", 
    status_code=status.HTTP_204_NO_CONTENT
)
def cancel_rsvp(
    event_id: int,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    rsvp = db.get(models.EventRSVP, (event_id, current_user.id))

    if rsvp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="RSVP not found",
        )

    if rsvp.check_in is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Cannot cancel after check-in",
        )

    db.delete(rsvp)
    db.commit()
