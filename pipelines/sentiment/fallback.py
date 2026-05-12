import json
import logging
import aiohttp
from pipelines.sentiment.provider import SentimentProvider, SentimentResult

logger = logging.getLogger(__name__)

class LlmApiProvider(SentimentProvider):
    """Provider that uses an LLM API (OpenAI) for sentiment analysis as a fallback."""
    
    def __init__(self, api_key: str | None = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"
        
    async def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment using OpenAI API."""
        if not self.api_key:
            logger.warning("LLM API key missing, returning neutral fallback")
            return SentimentResult(score=0.0, label="neutral", confidence=0.0)
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Prompt to get structured output
        prompt = (
            "Analyze the sentiment of the following product review. "
            "Respond ONLY with a JSON object containing 'label' (one of: positive, negative, neutral) "
            "and 'confidence' (float between 0 and 1).\n\n"
            f"Review: {text}"
        )
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"} if "gpt-4" in self.model or self.model == "gpt-3.5-turbo" else None
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.post(self.url, json=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"LLM API failed with status {resp.status}: {error_text}")
                        return SentimentResult(score=0.0, label="neutral", confidence=0.0)
                        
                    result = await resp.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Parse the JSON response from LLM
                    parsed = json.loads(content)
                    label = parsed.get("label", "neutral").lower()
                    confidence = parsed.get("confidence", 0.0)
                    
                    # Map label to score
                    score = 0.0
                    if "positive" in label:
                        score = 1.0
                        label = "positive"
                    elif "negative" in label:
                        score = -1.0
                        label = "negative"
                    else:
                        label = "neutral"
                        
                    return SentimentResult(score=score, label=label, confidence=confidence)
            except Exception as e:
                logger.error(f"Exception in LLM sentiment analysis: {e}")
                return SentimentResult(score=0.0, label="neutral", confidence=0.0)
