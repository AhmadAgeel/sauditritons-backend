from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from psycopg.errors import UniqueViolation

from app import models, schemas, utils, oauth2
from app.database import get_db
from app.config import settings
from app import refresh_tokens

from datetime import datetime, timedelta, timezone


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Create an account using the verified email link",
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(oauth2.get_current_user)):
    return current_user


@router.post("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    request: schemas.AccountDeletionRequest,
    response: Response,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    if request.confirm_email.lower() != current_user.email.lower():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Enter your account email exactly to confirm deletion")
    if current_user.role != "member":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Staff accounts must transfer their role before deletion")

    ticket_codes = list(db.scalars(select(models.EventRSVP.ticket_code).where(models.EventRSVP.user_id == current_user.id)).all())
    ticket_codes.extend(db.scalars(select(models.GuestEventRSVP.ticket_code).where(models.GuestEventRSVP.attendee_email == current_user.email.lower())).all())
    if ticket_codes:
        db.execute(delete(models.EventCheckIn).where(models.EventCheckIn.ticket_code.in_(ticket_codes)))
    db.execute(delete(models.MagicLink).where(models.MagicLink.email == current_user.email.lower()))
    db.execute(delete(models.GuestEventRSVP).where(models.GuestEventRSVP.attendee_email == current_user.email.lower()))
    db.execute(delete(models.AdminAuditLog).where(models.AdminAuditLog.actor_user_id == current_user.id))
    db.execute(delete(models.User).where(models.User.id == current_user.id))
    db.commit()
    refresh_tokens.delete_refresh_token_cookie(response)

@router.post("/me/activity", response_model=schemas.ActivityRecencyResponse)
def update_activity_recency(current_user: models.User = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    delta = timedelta(hours=settings.activity_recency_interval_hours)
    next_update_at = current_user.activity_recency_at + delta
    now = datetime.now(timezone.utc)

    if now < next_update_at:
        return schemas.ActivityRecencyResponse(
            activity_recency_at=current_user.activity_recency_at,
            next_update_at=next_update_at,
        )
    
    current_user.activity_recency_at = now
    db.commit()
    return schemas.ActivityRecencyResponse(
        activity_recency_at=now,
        next_update_at=now + delta,
    )
