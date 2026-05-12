import logging
from pipelines.sentiment.provider import SentimentProvider, SentimentResult

logger = logging.getLogger(__name__)

class SentimentService:
    """Service that orchestrates sentiment analysis using primary and fallback providers."""
    
    def __init__(self, primary: SentimentProvider, fallback: SentimentProvider | None = None):
        self.primary = primary
        self.fallback = fallback
        
    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment, falling back to secondary provider if primary fails or returns low confidence.
        
        Args:
            text: The text to analyze.
        """
        try:
            logger.debug("Attempting sentiment analysis with primary provider")
            result = await self.primary.analyze(text)
            
            # If result has 0 confidence, it might indicate a failure handled gracefully by the provider
            if result.confidence == 0.0 and self.fallback:
                logger.info("Primary provider returned zero confidence, trying fallback")
                return await self.fallback.analyze(text)
                
            return result
        except Exception as e:
            logger.warning(f"Primary sentiment provider failed: {e}")
            if self.fallback:
                logger.info("Trying fallback sentiment provider")
                try:
                    return await self.fallback.analyze(text)
                except Exception as fallback_err:
                    logger.error(f"Fallback sentiment provider also failed: {fallback_err}")
                    
            # Absolute fallback if everything fails
            return SentimentResult(score=0.0, label="neutral", confidence=0.0)
