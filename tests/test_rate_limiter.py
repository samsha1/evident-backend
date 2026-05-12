import pytest
from unittest.mock import AsyncMock, patch
from apps.api.src.services.rate_limiter import check_rate_limit
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_check_rate_limit_allowed():
    with patch("apps.api.src.services.rate_limiter.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value="5")
        mock_redis.incr = AsyncMock(return_value=6)
        
        await check_rate_limit("user123")
        
        mock_redis.get.assert_called_once_with("user:user123:daily")
        mock_redis.incr.assert_called_once_with("user:user123:daily")

@pytest.mark.asyncio
async def test_check_rate_limit_exceeded():
    with patch("apps.api.src.services.rate_limiter.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value="10")
        
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit("user123")
            
        assert exc_info.value.status_code == 429
        mock_redis.get.assert_called_once_with("user:user123:daily")
        mock_redis.incr.assert_not_called()

@pytest.mark.asyncio
async def test_check_rate_limit_first_request():
    with patch("apps.api.src.services.rate_limiter.redis_client") as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        
        await check_rate_limit("user123")
        
        mock_redis.get.assert_called_once_with("user:user123:daily")
        mock_redis.incr.assert_called_once_with("user:user123:daily")
        mock_redis.expire.assert_called_once()
