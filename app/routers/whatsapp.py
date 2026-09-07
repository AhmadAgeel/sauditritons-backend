import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app import models, schemas, oauth2
from app.database import get_db
from app.config import settings
from app.whatsapp_client import client, community_jid


router = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"],
)

def get_valid_ticket(
    token: str,
    db: Session,
) -> models.WhatsAppTicket:
    ticket = db.get(models.WhatsAppTicket, token)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite link",
        )

    if ticket.invite is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invite link has already been used",
        )

    expires_at = ticket.created_at + timedelta(
        days=settings.whatsapp_invite_exp_days
    )

    if datetime.now(timezone.utc) >= expires_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invite link has expired",
        )

    return ticket


@router.post("/tickets", response_model=schemas.WhatsAppTicketResponse)
def create_ticket(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    ticket = models.WhatsAppTicket(
        token=secrets.token_urlsafe(5),
        user_id=current_user.id,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get(
    "/tickets",
    response_model=list[schemas.WhatsAppTicketInfo],
)
def get_tickets(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(models.WhatsAppTicket)
        .options(
            selectinload(models.WhatsAppTicket.invite)
            .selectinload(models.WhatsAppInvite.join)
            .selectinload(models.WhatsAppJoin.wa_user)
        )
        .where(models.WhatsAppTicket.user_id == current_user.id)
        .order_by(models.WhatsAppTicket.created_at.desc())
    )

    return db.scalars(stmt).all()


@router.get("/invite/{token}", response_model=schemas.WhatsAppInviteResponse)
def get_invite(
    token: str,
    db: Session = Depends(get_db),
):
    ticket = get_valid_ticket(token, db)
    return {"inviter": ticket.user}


@router.post(
    "/invite/{token}/join",
    status_code=status.HTTP_303_SEE_OTHER,
    responses={
        303: {
            "description": "Invite consumed; browser redirects to WhatsApp.",
            "headers": {
                "Location": {
                    "description": "WhatsApp group invite URL",
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
async def use_ticket(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Consume the invite and redirect the browser to WhatsApp.

    This endpoint is browser-navigation-only. Do not call it with fetch or Axios.
    Submit a normal browser POST; the browser follows the 303 Location header.
    """
    ticket = get_valid_ticket(token, db)

    wa_inv_link = await client.get_group_invite_link(
        community_jid,
        revoke=True,
    )
    ticket.invite = models.WhatsAppInvite(
        wa_inv_link=wa_inv_link,
    )
    db.commit()

    return RedirectResponse(
        url=wa_inv_link,
        status_code=status.HTTP_303_SEE_OTHER,
    )

