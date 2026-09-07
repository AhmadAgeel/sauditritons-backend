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

    secret_key: str
    algorithm: str = "HS256"
    magic_link_expiration_minutes: int = 15

    activity_recency_interval_hours: int = 18

    whatsapp_community_jid: str
    whatsapp_announcements_jid: str
    whatsapp_invite_exp_days: int = 3

    zeptomail_api_url: str
    zeptomail_send_token: str
    auth_email_from: str
    magic_link_request_cooldown_minutes: int = 1

    redis_url: str
    magic_link_ip_limit: int = 10
    magic_link_ip_window_minutes: int = 10

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    cookie_secure: bool

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()