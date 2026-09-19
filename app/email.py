import logging
import time
from html import escape
from uuid import uuid4

import requests

from app.config import settings


logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def _sender() -> str:
        if "<" in settings.auth_email_from:
            return settings.auth_email_from
        return f"Saudi Students Association <{settings.auth_email_from}>"

    def send_magic_link(self, to_email: str, magic_link_url: str):
        client_reference = f"magic-link-{uuid4().hex}"
        safe_domain = escape(settings.display_domain)
        safe_url = escape(magic_link_url, quote=True)
        subject = f"Sign in to {settings.display_domain}"
        html_body = f"""
            <p>Use the secure link below to sign in to {safe_domain}:</p>
            <p><a href="{safe_url}">Sign in to {safe_domain}</a></p>
            <p>This link expires in {settings.magic_link_expiration_minutes} minutes.</p>
        """
        text_body = (
            f"Sign in to {settings.display_domain}: {magic_link_url}\n\n"
            f"This link expires in {settings.magic_link_expiration_minutes} minutes."
        )

        sender = self._send_postmark if settings.email_provider == "postmark" else self._send_zeptomail
        sender(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            client_reference=client_reference,
        )

    def _send_zeptomail(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        client_reference: str,
    ):
        if not settings.zeptomail_send_token:
            raise requests.RequestException("ZEPTOMAIL_SEND_TOKEN is not configured")
        payload = {
            "from": {"address": settings.auth_email_from, "name": "Saudi Students Association"},
            "to": [{"email_address": {"address": to_email}}],
            "subject": subject,
            "client_reference": client_reference,
            "htmlbody": html_body,
            "textbody": text_body,
            "track_clicks": False,
            "track_opens": False,
        }
        started_at = time.monotonic()
        response = requests.post(
            settings.zeptomail_api_url,
            json=payload,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": settings.zeptomail_send_token,
            },
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

    def _send_postmark(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        client_reference: str,
    ):
        if not settings.postmark_server_token:
            raise requests.RequestException("POSTMARK_SERVER_TOKEN is not configured")
        sender = (
            settings.auth_email_from
            if "<" in settings.auth_email_from
            else f"Saudi Students Association <{settings.auth_email_from}>"
        )
        payload = {
            "From": sender,
            "To": to_email,
            "Subject": subject,
            "HtmlBody": html_body,
            "TextBody": text_body,
            "MessageStream": "outbound",
            "Tag": "authentication",
            "TrackOpens": False,
            "TrackLinks": "None",
            "Metadata": {"client_reference": client_reference},
        }
        if settings.auth_email_reply_to:
            payload["ReplyTo"] = settings.auth_email_reply_to

        started_at = time.monotonic()
        response = requests.post(
            settings.postmark_api_url,
            json=payload,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "X-Postmark-Server-Token": settings.postmark_server_token,
            },
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()
        logger.info(
            "Postmark accepted magic-link email client_reference=%s message_id=%s elapsed_ms=%d",
            client_reference,
            body.get("MessageID", "unknown"),
            round((time.monotonic() - started_at) * 1000),
        )


email_service = EmailService()
