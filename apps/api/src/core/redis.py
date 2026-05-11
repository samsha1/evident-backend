import redis.asyncio as aioredis

from apps.api.src.core.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency that returns the shared Redis client."""
    return redis_client
