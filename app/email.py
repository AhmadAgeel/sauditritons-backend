import logging
import time
from html import escape
from uuid import uuid4

import requests

from app.config import settings


logger = logging.getLogger(__name__)


class EmailService:
    def send_magic_link(
        self,
        to_email: str,
        magic_link_url: str,
    ):
        client_reference = f"magic-link-{uuid4().hex}"
        safe_domain = escape(settings.display_domain)
        safe_url = escape(magic_link_url, quote=True)
        payload = {
            "from": {
                "address": settings.auth_email_from,
                "name": "Saudi Students Association",
            },
            "to": [
                {
                    "email_address": {
                        "address": to_email,
                    }
                }
            ],
            "subject": f"Sign in to {settings.display_domain}",
            "client_reference": client_reference,
            "htmlbody": f"""
                <p>Use the secure link below to sign in to {safe_domain}:</p>

                <p>
                    <a href="{safe_url}">
                        Sign in to {safe_domain}
                    </a>
                </p>

                <p>This link expires in
                {settings.magic_link_expiration_minutes} minutes.</p>
            """,
            "textbody": (
                f"Sign in to {settings.display_domain}: {magic_link_url}\n\n"
                f"This link expires in {settings.magic_link_expiration_minutes} minutes."
            ),
            "track_clicks": False,
            "track_opens": False,
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": settings.zeptomail_send_token,
        }

        started_at = time.monotonic()
        response = requests.post(
            settings.zeptomail_api_url,
            json=payload,
            headers=headers,
            timeout=10,
        )

        response.raise_for_status()
        try:
            request_id = response.json().get("request_id", "unknown")
        except (requests.JSONDecodeError, ValueError):
            request_id = "unknown"
        logger.info(
            "ZeptoMail accepted magic-link email client_reference=%s request_id=%s elapsed_ms=%d",
            client_reference,
            request_id,
            round((time.monotonic() - started_at) * 1000),
        )


email_service = EmailService()
