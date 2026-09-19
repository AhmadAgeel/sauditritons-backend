import logging
from uuid import uuid4

import requests
from fastapi import HTTPException, status

from app.config import settings


logger = logging.getLogger(__name__)


def turnstile_enabled() -> bool:
    return bool(settings.turnstile_secret_key.strip())


def verify_turnstile(token: str | None, remote_ip: str | None = None) -> None:
    """Validate a one-time Turnstile token when production protection is enabled."""
    if not turnstile_enabled():
        return
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete the security check and try again.",
        )

    payload = {
        "secret": settings.turnstile_secret_key,
        "response": token,
        "idempotency_key": str(uuid4()),
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(settings.turnstile_verify_url, data=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning("Turnstile verification service failed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The security check is temporarily unavailable. Please try again.",
        ) from error

    allowed_hostnames = {
        hostname.strip().lower()
        for hostname in settings.turnstile_allowed_hostnames.split(",")
        if hostname.strip()
    }
    hostname = str(result.get("hostname", "")).strip().lower()
    action = str(result.get("action", "")).strip()
    valid = (
        result.get("success") is True
        and action == "guest_rsvp"
        and (not allowed_hostnames or hostname in allowed_hostnames)
    )
    if not valid:
        logger.info(
            "Turnstile rejected guest RSVP: codes=%s action=%s hostname=%s",
            result.get("error-codes", []),
            action,
            hostname,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The security check expired or could not be verified. Please try again.",
        )
