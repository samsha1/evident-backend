import redis.asyncio as redis
from apps.api.src.core.config import settings
import json
from typing import Any, Optional

redis_client = redis.from_url(settings.KV_URL, decode_responses=True)

async def get_product_cache(product_id: str) -> Optional[dict]:
    data = await redis_client.get(f"product:{product_id}")
    if data:
        return json.loads(data)
    return None

async def set_product_cache(product_id: str, data: dict, ttl_seconds: int = 10800):
    await redis_client.setex(f"product:{product_id}", ttl_seconds, json.dumps(data))
