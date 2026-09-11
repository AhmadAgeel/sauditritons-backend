from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from app import schemas, models
from app.config import settings
from app.database import get_db

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy import select
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(claims: dict) -> str:
    token_claims = claims.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    token_claims["exp"] = expire

    encoded_jwt = jwt.encode(
        token_claims,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError:
        raise credentials_exception

    sub = payload.get("sub")

    if sub is None:
        raise credentials_exception

    token_data = schemas.TokenData(sub=sub)

    return token_data


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_access_token(token, credentials_exception)

    statement = select(models.User).where(models.User.id == int(token_data.sub))
    user = db.execute(statement).scalar_one_or_none()

    if user is None or not user.email.lower().endswith("@ucsd.edu"):
        raise credentials_exception

    return user


def get_current_staff(current_user: models.User = Depends(get_current_user)):
    if current_user.role not in {"content_editor", "officer", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return current_user


def get_current_officer(current_user: models.User = Depends(get_current_user)):
    if current_user.role not in {"officer", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Officer access required")
    return current_user


def get_current_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
