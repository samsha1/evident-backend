from apps.api.src.services.cache import redis_client
from apps.api.src.core.config import settings
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

async def check_rate_limit(user_id: str):
    """Check if user has exceeded their daily limit.
    
    Enforced via Redis INCR with daily TTL (resets at midnight UTC).
    """
    # Bypass for admin or special users if needed
    # For now, apply to everyone
    
    key = f"user:{user_id}:daily"
    count = await redis_client.get(key)
    
    if count and int(count) >= settings.DEFAULT_DAILY_LIMIT:
        logger.warning(f"Rate limit exceeded for user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily limit of {settings.DEFAULT_DAILY_LIMIT} requests exceeded.",
        )
        
    # Increment
    new_count = await redis_client.incr(key)
    
    # Set TTL to midnight UTC on first request of the day
    if new_count == 1:
        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_midnight = int((midnight - now).total_seconds())
        
        # Ensure we set at least 1 second
        seconds_until_midnight = max(1, seconds_until_midnight)
        
        await redis_client.expire(key, seconds_until_midnight)
        logger.info(f"Set rate limit TTL for {user_id} to {seconds_until_midnight} seconds")
        
    return new_count
