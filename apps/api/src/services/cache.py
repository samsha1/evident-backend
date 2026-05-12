import redis.asyncio as redis
from apps.api.src.core.config import settings
import json
from typing import Any, Optional
from datetime import datetime, timezone

# Fix: Use REDIS_URL instead of KV_URL which was missing in config
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_product_cache(asin: str) -> tuple[Optional[dict], str]:
    """Get cached product result and its status.
    
    Returns:
        tuple: (cached_data, status)
        where status is 'fresh', 'stale', or 'miss'
    """
    data = await redis_client.get(f"product:{asin}")
    if not data:
        return None, "miss"
        
    try:
        cached_json = json.loads(data)
        computed_at_str = cached_json.get("computed_at")
        
        if not computed_at_str:
            return cached_json, "stale" # Assume stale if no timestamp
            
        computed_at = datetime.fromisoformat(computed_at_str)
        # Ensure timezone awareness for comparison
        if computed_at.tzinfo is None:
            computed_at = computed_at.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        elapsed = now - computed_at
        
        # Fresh if less than 3 hours old
        if elapsed.total_seconds() < 3 * 3600:
            return cached_json, "fresh"
        # Stale if less than 24 hours old
        elif elapsed.total_seconds() < 24 * 3600:
            return cached_json, "stale"
        else:
            return None, "miss" # Treat as miss if older than 24 hours
            
    except Exception as e:
        print(f"Error reading cache for {asin}: {e}")
        return None, "miss"

async def set_product_cache(asin: str, data: dict, ttl_seconds: int = 86400):
    """Set product cache with TTL (default 24 hours)."""
    # Ensure computed_at is set
    if "computed_at" not in data:
        data["computed_at"] = datetime.now(timezone.utc).isoformat()
        
    await redis_client.setex(f"product:{asin}", ttl_seconds, json.dumps(data))

async def acquire_lock(asin: str, timeout: int = 30) -> bool:
    """Acquire a distributed lock for an ASIN."""
    return await redis_client.set(f"product:lock:{asin}", "locked", ex=timeout, nx=True)

async def release_lock(asin: str):
    """Release the distributed lock."""
    await redis_client.delete(f"product:lock:{asin}")

async def subscribe_to_channel(asin: str):
    """Subscribe to a pub/sub channel for an ASIN."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"product:{asin}:channel")
    return pubsub

async def publish_to_channel(asin: str, data: dict):
    """Publish data to a pub/sub channel for an ASIN."""
    await redis_client.publish(f"product:{asin}:channel", json.dumps(data))
