import hashlib
import secrets

from fastapi import Response

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app import models
from app.config import settings


def create_refresh_token(
    user_id: int,
    db: Session,
) -> str:
    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode()
    ).hexdigest()

    refresh_token = models.RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )

    db.add(refresh_token)

    return token


def set_refresh_token_cookie(
    response: Response,
    token: str,
):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="none" if settings.cookie_secure else "lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/auth",
    )


def delete_refresh_token_cookie(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
    )