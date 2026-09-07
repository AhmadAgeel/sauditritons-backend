import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.redis import async_redis_client

from sse_starlette.sse import EventSourceResponse

router = APIRouter(
    prefix="/ticket",
    tags=["Tickets"],
)


@router.get(
    "/{ticket_code}",
    response_model=schemas.PublicTicketResponse,
)
def get_ticket(
    ticket_code: str,
    db: Session = Depends(get_db),
):
    normalized_code = ticket_code.replace("-", "").upper()

    stmt = (
        select(models.EventRSVP)
        .options(
            joinedload(models.EventRSVP.event),

            joinedload(models.EventRSVP.user),

            joinedload(models.EventRSVP.check_in)
            .joinedload(models.EventCheckIn.workspace_user),
        )
        .where(models.EventRSVP.ticket_code == normalized_code)
    )

    rsvp = db.scalar(stmt)

    if rsvp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return rsvp


@router.get("/{ticket_code}/events")
async def ticket_events(
    ticket_code: str,
):
    """
    SSE stream for live ticket check-in updates.

    Sends:
    - ready: connection established
    - checked_in: JSON containing checked_in_at and scanned_by

    Closes after the ticket is checked in.
    """

    normalized_code = ticket_code.replace("-", "").upper()

    async def event_generator():
        channel = f"ticket:{normalized_code}"

        async with async_redis_client.pubsub() as pubsub:
            await pubsub.subscribe(channel)

            # Subscription is now active.
            yield {
                "event": "ready",
                "data": "",
            }

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                payload = schemas.TicketCheckInEvent.model_validate_json(
                    message["data"]
                )

                yield {
                    "event": "checked_in",
                    "data": payload.model_dump_json(),
                }

                # A ticket can only be checked in once.
                return

    return EventSourceResponse(event_generator())
