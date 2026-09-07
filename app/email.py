import requests

from app.config import settings


class EmailService:
    def send_magic_link(
        self,
        to_email: str,
        magic_link_url: str,
    ):
        payload = {
            "from": {
                "address": settings.auth_email_from,
                "name": "SSA Auth",
            },
            "to": [
                {
                    "email_address": {
                        "address": to_email,
                    }
                }
            ],
            "subject": f"Sign in to {settings.display_domain}",
            "htmlbody": f"""
                <p>Click below to sign in:</p>

                <p>
                    <a href="{magic_link_url}">
                        Sign in to {settings.display_domain}
                    </a>
                </p>

                <p>This link expires in
                {settings.magic_link_expiration_minutes} minutes.</p>
            """,
            "track_clicks": False,
            "track_opens": False,
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": settings.zeptomail_send_token,
        }

        response = requests.post(
            settings.zeptomail_api_url,
            json=payload,
            headers=headers,
            timeout=10,
        )

        response.raise_for_status()


email_service = EmailService()