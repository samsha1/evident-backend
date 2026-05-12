from typing import Any
from pydantic import BaseModel
from pipelines.sentiment.provider import SentimentResult

class VerdictInput(BaseModel):
    """Input for verdict computation."""
    review_id: str
    source: str
    sentiment: SentimentResult

class VerdictResult(BaseModel):
    """Result of verdict computation."""
    verdict: str
    confidence: float
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    total_reviews: int
    sources_json: dict[str, Any]

def compute_verdict(inputs: list[VerdictInput]) -> VerdictResult:
    """Compute aggregated verdict from a list of analyzed reviews.
    
    Args:
        inputs: List of VerdictInput objects containing sentiment results.
    """
    total = len(inputs)
    if total == 0:
        return VerdictResult(
            verdict="unknown",
            confidence=0.0,
            positive_pct=0.0,
            negative_pct=0.0,
            neutral_pct=0.0,
            total_reviews=0,
            sources_json={},
        )
        
    pos = sum(1 for i in inputs if i.sentiment.label == "positive")
    neg = sum(1 for i in inputs if i.sentiment.label == "negative")
    neu = sum(1 for i in inputs if i.sentiment.label == "neutral")
    
    pos_pct = pos / total
    neg_pct = neg / total
    neu_pct = neu / total
    
    # Simple verdict logic for MVP
    if pos_pct > 0.6:
        verdict = "recommended"
    elif neg_pct > 0.4:
        verdict = "avoid"
    else:
        verdict = "mixed"
        
    # Confidence based on average sentiment confidence and review volume
    avg_conf = sum(i.sentiment.confidence for i in inputs) / total
    # Scale confidence by review count (reach 100% of avg_conf at 10 reviews)
    volume_factor = min(total / 10.0, 1.0)
    confidence = avg_conf * volume_factor
    
    # Group by source
    sources = {}
    for i in inputs:
        src = i.source
        if src not in sources:
            sources[src] = {"total": 0, "positive": 0, "negative": 0}
        sources[src]["total"] += 1
        if i.sentiment.label == "positive":
            sources[src]["positive"] += 1
        elif i.sentiment.label == "negative":
            sources[src]["negative"] += 1
            
    return VerdictResult(
        verdict=verdict,
        confidence=confidence,
        positive_pct=pos_pct,
        negative_pct=neg_pct,
        neutral_pct=neu_pct,
        total_reviews=total,
        sources_json=sources,
    )
