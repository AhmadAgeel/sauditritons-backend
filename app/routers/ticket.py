import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.redis import async_redis_client
from app.rate_limits import public_ticket_ip_rate_limit
from app.config import settings
from app.wallet_pass import WalletNotConfiguredError, WalletServiceError, build_event_pass, wallet_is_configured, wallet_provider

from sse_starlette.sse import EventSourceResponse

router = APIRouter(
    prefix="/ticket",
    tags=["Tickets"],
)


@router.get("/wallet/status")
def wallet_status():
    return {"available": wallet_is_configured(), "provider": wallet_provider()}


@router.get(
    "/{ticket_code}",
    response_model=schemas.PublicTicketResponse,
)
def get_ticket(
    ticket_code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    public_ticket_ip_rate_limit(request)
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

    if rsvp is not None:
        return rsvp

    guest = db.scalar(
        select(models.GuestEventRSVP)
        .options(joinedload(models.GuestEventRSVP.event), joinedload(models.GuestEventRSVP.check_in).joinedload(models.EventCheckIn.workspace_user))
        .where(models.GuestEventRSVP.ticket_code == normalized_code)
    )
    if guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return {"ticket_code": guest.ticket_code, "event": guest.event, "user": None, "attendee_name": guest.attendee_name, "companion_names": guest.companion_names, "check_in": guest.check_in}


@router.get("/{ticket_code}/wallet")
def download_wallet_pass(ticket_code: str, request: Request, db: Session = Depends(get_db)):
    public_ticket_ip_rate_limit(request)
    normalized_code = ticket_code.replace("-", "").upper()
    member = db.scalar(
        select(models.EventRSVP)
        .options(joinedload(models.EventRSVP.event), joinedload(models.EventRSVP.user))
        .where(models.EventRSVP.ticket_code == normalized_code)
    )
    guest = None
    if member is None:
        guest = db.scalar(
            select(models.GuestEventRSVP)
            .options(joinedload(models.GuestEventRSVP.event))
            .where(models.GuestEventRSVP.ticket_code == normalized_code)
        )
    registration = member or guest
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    holder_name = f"{member.user.first_name} {member.user.last_name}" if member else guest.attendee_name
    try:
        content = build_event_pass(
            ticket_code=normalized_code,
            holder_name=holder_name,
            companion_count=len(registration.companion_names),
            event=registration.event,
        )
    except WalletNotConfiguredError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Apple Wallet passes are not configured yet")
    except WalletServiceError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Apple Wallet signing credentials are invalid")
    return Response(
        content=content,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f'attachment; filename="ssa-{normalized_code}.pkpass"'},
    )


@router.get("/{ticket_code}/events")
async def ticket_events(
    ticket_code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    SSE stream for live ticket check-in updates.

    Sends:
    - ready: connection established
    - checked_in: JSON containing checked_in_at and scanned_by

    Closes after the ticket is checked in.
    """

    normalized_code = ticket_code.replace("-", "").upper()
    public_ticket_ip_rate_limit(request)

    member_exists = db.scalar(select(models.EventRSVP.ticket_code).where(models.EventRSVP.ticket_code == normalized_code))
    guest_exists = None if member_exists else db.scalar(
        select(models.GuestEventRSVP.ticket_code).where(models.GuestEventRSVP.ticket_code == normalized_code)
    )
    if member_exists is None and guest_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    async def event_generator():
        channel = f"ticket:{normalized_code}"

        async with async_redis_client.pubsub() as pubsub:
            await pubsub.subscribe(channel)

            # Subscription is now active.
            yield {
                "event": "ready",
                "data": "",
            }

            try:
                async with asyncio.timeout(settings.ticket_stream_max_minutes * 60):
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
            except TimeoutError:
                return

    return EventSourceResponse(event_generator())
