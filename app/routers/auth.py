from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import models, schemas, utils, oauth2
from app.database import get_db
from app.email import email_service
from app.rate_limits import magic_link_ip_rate_limit
from app.config import settings

import requests
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app import refresh_tokens


router = APIRouter(prefix="/auth", tags=["Auth"])


def get_valid_magic_link(
    token: str,
    db: Session,
):
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    stmt = select(models.MagicLink).where(
        models.MagicLink.token_hash == token_hash
    ).with_for_update()

    magic_link = db.scalar(stmt)

    if magic_link is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid magic link",
        )

    if magic_link.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Magic link revoked",
        )

    now = datetime.now(timezone.utc)

    if magic_link.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Magic link already used",
        )

    if now >= magic_link.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Magic link expired",
        )

    return magic_link


@router.post("/login", response_model=schemas.Token)
def login(
    response: Response,
    user_credentials: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    statement = select(models.User).where(models.User.email == user_credentials.username.lower())
    user = db.execute(statement).scalar_one_or_none()

    if (
        user is None
        or user.password_hash is None
        or not utils.verify_password(
            user_credentials.password,
            user.password_hash
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid credentials",
        )
  
    access_token = oauth2.create_access_token({"sub": str(user.id)})

    refresh_token = refresh_tokens.create_refresh_token(
        user_id=user.id,
        db=db,
    )

    db.commit()

    refresh_tokens.set_refresh_token_cookie(
        response=response,
        token=refresh_token,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post(
    "/refresh",
    response_model=schemas.Token,
)
def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    token_hash = hashlib.sha256(
        refresh_token.encode()
    ).hexdigest()

    stored_token = db.scalar(
        select(models.RefreshToken)
        .where(models.RefreshToken.token_hash == token_hash)
        .with_for_update()
    )

    now = datetime.now(timezone.utc)

    if (
        stored_token is None
        or stored_token.revoked_at is not None
        or now >= stored_token.expires_at
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = db.get(
        models.User,
        stored_token.user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    stored_token.revoked_at = now

    new_refresh_token = refresh_tokens.create_refresh_token(
        user_id=user.id,
        db=db,
    )

    db.commit()

    refresh_tokens.set_refresh_token_cookie(
        response=response,
        token=new_refresh_token,
    )

    return {
        "access_token": oauth2.create_access_token(
            {"sub": str(user.id)}
        ),
        "token_type": "bearer",
    }


@router.post(
    "/magic-link/request",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(magic_link_ip_rate_limit)],
)
def request_magic_link(
    request: schemas.MagicLinkRequest,
    db: Session = Depends(get_db),
):
    email = request.email.lower()
    now = datetime.now(timezone.utc)

    latest_magic_link = db.scalar(
        select(models.MagicLink)
        .where(models.MagicLink.email == email)
        .order_by(models.MagicLink.created_at.desc())
        .limit(1)
    )

    if (
        latest_magic_link is not None
        and now
        < latest_magic_link.created_at
        + timedelta(
            minutes=settings.magic_link_request_cooldown_minutes
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another magic link",
        )

    # Revoke previous active links
    db.execute(
        update(models.MagicLink)
        .where(
            models.MagicLink.email == email,
            now < models.MagicLink.expires_at,
            models.MagicLink.revoked_at.is_(None),
            models.MagicLink.used_at.is_(None),
        )
        .values(revoked_at=now)
    )

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    magic_link = models.MagicLink(
        email=email,
        token_hash=token_hash,
        expires_at=now + timedelta(
            minutes=settings.magic_link_expiration_minutes
        ),
    )

    db.add(magic_link)

    # Revoke old + create new atomically
    db.commit()

    magic_link_url = (
        f"{settings.frontend_url}/auth/magic?token={token}"
    )

    try:
        email_service.send_magic_link(
            to_email=email,
            magic_link_url=magic_link_url,
        )
    except requests.RequestException as e:
        print(e.response.status_code, e.response.text)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send magic link email",
        )


@router.post(
    "/magic-link/verify", 
    response_model=schemas.MagicLinkVerifyResponse,
)
def verify_magic_link(
    request: schemas.MagicLinkVerify,
    response: Response,
    db: Session = Depends(get_db),
):
    magic_link = get_valid_magic_link(
        request.token,
        db,
    )

    user = db.scalar(
        select(models.User).where(
            models.User.email == magic_link.email
        )
    )

    if user is None:
        return {
            "signup_required": True,
            "auth": None,
        }

    magic_link.used_at = datetime.now(timezone.utc)

    refresh_token = refresh_tokens.create_refresh_token(
        user_id=user.id,
        db=db,
    )

    db.commit()

    refresh_tokens.set_refresh_token_cookie(
        response=response,
        token=refresh_token,
    )

    access_token = oauth2.create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "signup_required": False,
        "auth": {
            "access_token": access_token,
            "token_type": "bearer",
        },
    }


@router.post("/complete-signup", response_model=schemas.Token)
def complete_signup(
    request: schemas.CompleteSignup,
    response: Response,
    db: Session = Depends(get_db),
):
    magic_link = get_valid_magic_link(
        request.token,
        db,
    )

    user = db.scalar(
        select(models.User).where(
            models.User.email == magic_link.email
        )
    )

    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists",
        )

    password_hash = None

    if request.password is not None:
        password_hash = utils.hash_password(request.password)

    user = models.User(
        email=magic_link.email,
        password_hash=password_hash,
        first_name=request.first_name,
        last_name=request.last_name,
    )

    db.add(user)
    magic_link.used_at = datetime.now(timezone.utc)

    try:
        db.flush()  # inserts user so user.id becomes available

        refresh_token = refresh_tokens.create_refresh_token(
            user_id=user.id,
            db=db,
        )

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists",
        )

    db.refresh(user)

    refresh_tokens.set_refresh_token_cookie(
        response=response,
        token=refresh_token,
    )

    access_token = oauth2.create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if refresh_token is not None:
        token_hash = hashlib.sha256(
            refresh_token.encode()
        ).hexdigest()

        stored_token = db.scalar(
            select(models.RefreshToken).where(
                models.RefreshToken.token_hash == token_hash
            )
        )

        if (
            stored_token is not None 
            and stored_token.revoked_at is None
        ):
            stored_token.revoked_at = datetime.now(timezone.utc)
            db.commit()

    refresh_tokens.delete_refresh_token_cookie(response)








