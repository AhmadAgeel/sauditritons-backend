import redis
import redis.asyncio as async_redis

from app.config import settings


redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True,
)

async_redis_client = async_redis.from_url(
    settings.redis_url,
    decode_responses=True,
)