from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SaudiTritons API"
    environment: str = "development"
    frontend_url: str
    display_domain: str

    database_hostname: str
    database_port: int = 5432
    database_name: str
    database_username: str
    database_password: str

    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    magic_link_expiration_minutes: int = 15

    activity_recency_interval_hours: int = 18

    whatsapp_community_jid: str
    whatsapp_announcements_jid: str
    whatsapp_invite_exp_days: int = 3
    whatsapp_enabled: bool = True

    zeptomail_api_url: str
    zeptomail_send_token: str
    auth_email_from: str
    magic_link_request_cooldown_minutes: int = 1

    redis_url: str
    magic_link_ip_limit: int = 10
    magic_link_ip_window_minutes: int = 10
    password_login_email_limit: int = 8
    password_login_email_window_minutes: int = 15
    guest_rsvp_ip_limit: int = 12
    guest_rsvp_ip_window_minutes: int = 60
    public_ticket_ip_limit: int = 60
    public_ticket_ip_window_minutes: int = 1
    ticket_stream_max_minutes: int = 20
    max_request_bytes: int = 3_000_000

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    cookie_secure: bool
    bootstrap_admin_email: str = ""

    apple_wallet_pass_type_identifier: str = ""
    apple_wallet_team_identifier: str = ""
    apple_wallet_organization_name: str = "Saudi Students Association at UC San Diego"
    apple_wallet_signing_cert_base64: str = ""
    apple_wallet_signing_key_base64: str = ""
    apple_wallet_signing_key_password: str = ""
    apple_wallet_wwdr_cert_base64: str = ""
    walletwallet_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
