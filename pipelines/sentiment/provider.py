import asyncio
from typing import Protocol, runtime_checkable
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SentimentResult(BaseModel):
    """Result of sentiment analysis for a text."""
    score: float  # -1.0 (negative) to 1.0 (positive)
    label: str    # "positive", "negative", "neutral"
    confidence: float

@runtime_checkable
class SentimentProvider(Protocol):
    """Protocol for sentiment analysis providers."""
    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of a text."""
        ...

class LocalTransformerProvider(SentimentProvider):
    """Provider that uses a local Hugging Face transformer model."""
    
    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"):
        self.model_name = model_name
        self.pipe = None
        
    def load(self) -> None:
        """Load the model. Should be called at startup."""
        from transformers import pipeline
        logger.info(f"Loading transformer model: {self.model_name}")
        # pipeline handles tokenization and inference
        self.pipe = pipeline("sentiment-analysis", model=self.model_name)
        logger.info("Model loaded successfully")
        
    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment using the local model."""
        if not self.pipe:
            self.load()
            
        # Run synchronous pipeline in an executor to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, self._sync_analyze, text)
            return result
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            # Return neutral as fallback
            return SentimentResult(score=0.0, label="neutral", confidence=0.0)
        
    def _sync_analyze(self, text: str) -> SentimentResult:
        """Synchronous analysis called in executor."""
        if not self.pipe:
            raise RuntimeError("Model not loaded")
            
        output = self.pipe(text)[0]
        label = output["label"]
        score = output["score"]
        
        # Map label to score
        # For cardiffnlp/twitter-roberta-base-sentiment-latest:
        # labels are usually "negative", "neutral", "positive"
        # but can also be "LABEL_0", "LABEL_1", "LABEL_2"
        
        lbl_lower = label.lower()
        if "pos" in lbl_lower or "2" in lbl_lower:
            return SentimentResult(score=1.0, label="positive", confidence=score)
        elif "neg" in lbl_lower or "0" in lbl_lower:
            return SentimentResult(score=-1.0, label="negative", confidence=score)
        else:
            return SentimentResult(score=0.0, label="neutral", confidence=score)


class LlmApiProvider(SentimentProvider):
    """Provider that uses an external LLM API (OpenAI) for sentiment analysis."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment using OpenAI API."""
        if not self.api_key:
            logger.warning("OpenAI API key missing, returning neutral.")
            return SentimentResult(score=0.0, label="neutral", confidence=0.0)
            
        import aiohttp
        import json
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a sentiment analysis tool. Respond with a JSON object containing 'score' (between -1.0 and 1.0), 'label' (one of 'positive', 'negative', 'neutral'), and 'confidence' (between 0.0 and 1.0)."},
                {"role": "user", "content": f"Analyze this text: {text}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"OpenAI API error: {resp.status}")
                        return SentimentResult(score=0.0, label="neutral", confidence=0.0)
                        
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    result = json.loads(content)
                    return SentimentResult(
                        score=float(result.get("score", 0.0)),
                        label=result.get("label", "neutral"),
                        confidence=float(result.get("confidence", 0.0))
                    )
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return SentimentResult(score=0.0, label="neutral", confidence=0.0)
