import json

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.redis import redis_client

router = APIRouter(
    prefix="/internal/events",
    tags=["Internal Events"],
)

@router.post(
    "/",
    response_model=schemas.EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
):
    new_event = models.Event(**event.model_dump())

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event


@router.get(
    "/",
    response_model=list[schemas.EventResponse],
)
def get_events(
    db: Session = Depends(get_db),
):
    stmt = (
        select(models.Event)
        .order_by(models.Event.starts_at.desc())
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

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event


@router.patch(
    "/{event_id}",
    response_model=schemas.EventResponse,
)
def update_event(
    event_id: int,
    update: schemas.EventUpdate,
    db: Session = Depends(get_db),
):
    event = db.get(models.Event, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)

    return event


@router.post(
    "/{event_id}/check-ins",
    response_model=schemas.EventCheckInResponse,
)
def create_check_in(
    event_id: int,
    check_in: schemas.EventCheckInCreate,
    db: Session = Depends(get_db),
):
    ticket_code = check_in.ticket_code.replace("-", "").upper()

    rsvp = db.scalar(
        select(models.EventRSVP)
        .where(models.EventRSVP.ticket_code == ticket_code)
    )

    if rsvp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if rsvp.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is not for this event",
        )

    if rsvp.check_in is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket already checked in",
        )

    event = db.get(models.Event, event_id)

    if check_in.method == "qr":
        if check_in.mark_paid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR check-in cannot mark payment",
            )

        if event.is_paid and not rsvp.has_paid:
            return {
                "status": "payment_required",
                "ticket_code": ticket_code,
                "has_paid": False,
            }

    elif check_in.method == "manual" and check_in.mark_paid:
        rsvp.has_paid = True

    workspace_user = db.get(
        models.WorkspaceUser,
        check_in.workspace_user_id,
    )

    if workspace_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace user not found",
        )

    new_check_in = models.EventCheckIn(
        ticket_code=ticket_code,
        workspace_user_id=check_in.workspace_user_id,
        method=check_in.method,
    )

    db.add(new_check_in)
    db.commit()

    db.refresh(new_check_in)

    redis_client.publish(
        f"ticket:{ticket_code}",
        json.dumps({
            "checked_in_at": new_check_in.checked_in_at.isoformat(),
            "scanned_by": workspace_user.display_name,
        }),
    )

    return {
        "status": "checked_in",
        "ticket_code": ticket_code,
        "has_paid": rsvp.has_paid,
    }


@router.get(
    "/{event_id}/rsvps",
    response_model=list[schemas.InternalEventRSVPResponse],
)
def get_event_rsvps(
    event_id: int,
    db: Session = Depends(get_db),
):
    event = db.get(models.Event, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    stmt = (
        select(models.EventRSVP)
        .options(
            selectinload(models.EventRSVP.user),
            selectinload(models.EventRSVP.check_in)
            .selectinload(models.EventCheckIn.workspace_user),
        )
        .where(models.EventRSVP.event_id == event_id)
        .order_by(models.EventRSVP.created_at)
    )

    return db.scalars(stmt).all()
