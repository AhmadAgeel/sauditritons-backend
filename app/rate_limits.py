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

def magic_link_ip_rate_limit(request: Request):
    if not magic_link_ip_limiter.try_acquire(request.client.host):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )

