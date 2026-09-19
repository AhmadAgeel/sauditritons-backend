from fastapi import HTTPException, Request, status
from pyrate_limiter import Duration, Limiter, Rate, RedisBucket

from app.redis import redis_client
from app.config import settings


magic_link_ip_bucket = RedisBucket.init(
    [
        Rate(  # Rate(x, y) means x requests per y duration
            settings.magic_link_ip_limit,
            Duration.MINUTE * settings.magic_link_ip_window_minutes,
        )
    ],
    redis_client,
    "magic_link_ip",
)

magic_link_ip_limiter = Limiter(
    magic_link_ip_bucket
)

password_login_email_limiter = Limiter(RedisBucket.init(
    [Rate(settings.password_login_email_limit, Duration.MINUTE * settings.password_login_email_window_minutes)],
    redis_client,
    "password_login_email",
))

guest_rsvp_ip_limiter = Limiter(RedisBucket.init(
    [Rate(settings.guest_rsvp_ip_limit, Duration.MINUTE * settings.guest_rsvp_ip_window_minutes)],
    redis_client,
    "guest_rsvp_ip",
))

public_ticket_ip_limiter = Limiter(RedisBucket.init(
    [Rate(settings.public_ticket_ip_limit, Duration.MINUTE * settings.public_ticket_ip_window_minutes)],
    redis_client,
    "public_ticket_ip",
))


def _request_host(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _enforce(limiter: Limiter, key: str):
    # pyrate-limiter blocks indefinitely by default once a bucket is full.
    # API throttles must fail fast so an attacker cannot occupy worker threads.
    if not limiter.try_acquire(key, blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )

def magic_link_ip_rate_limit(request: Request):
    _enforce(magic_link_ip_limiter, _request_host(request))


def password_login_email_rate_limit(email: str):
    _enforce(password_login_email_limiter, email)


def guest_rsvp_ip_rate_limit(request: Request):
    _enforce(guest_rsvp_ip_limiter, _request_host(request))


def public_ticket_ip_rate_limit(request: Request):
    _enforce(public_ticket_ip_limiter, _request_host(request))
