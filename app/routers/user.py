from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from psycopg.errors import UniqueViolation

from app import models, schemas, utils, oauth2
from app.database import get_db
from app.config import settings

from datetime import datetime, timedelta, timezone


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        password_hash=utils.hash_password(user.password),
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        if isinstance(exc.orig, UniqueViolation):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        raise

    db.refresh(new_user)
    return new_user


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(oauth2.get_current_user)):
    return current_user

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
