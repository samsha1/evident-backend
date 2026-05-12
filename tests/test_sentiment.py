import pytest
from unittest.mock import AsyncMock, MagicMock
from pipelines.sentiment.service import SentimentService
from pipelines.sentiment.provider import SentimentResult

@pytest.mark.asyncio
async def test_sentiment_service_primary_success():
    """Test that SentimentService uses primary provider when it succeeds."""
    mock_primary = MagicMock()
    mock_primary.analyze = AsyncMock(return_value=SentimentResult(score=1.0, label="positive", confidence=0.9))
    
    service = SentimentService(primary=mock_primary)
    result = await service.analyze("test")
    
    assert result.label == "positive"
    mock_primary.analyze.assert_called_once_with("test")

@pytest.mark.asyncio
async def test_sentiment_service_fallback():
    """Test that SentimentService falls back when primary fails."""
    mock_primary = MagicMock()
    mock_primary.analyze = AsyncMock(side_effect=Exception("Failed"))
    
    mock_fallback = MagicMock()
    mock_fallback.analyze = AsyncMock(return_value=SentimentResult(score=-1.0, label="negative", confidence=0.8))
    
    service = SentimentService(primary=mock_primary, fallback=mock_fallback)
    result = await service.analyze("test")
    
    assert result.label == "negative"
    mock_fallback.analyze.assert_called_once_with("test")
