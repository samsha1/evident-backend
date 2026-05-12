from fastapi import APIRouter, Depends, Request, Query
from sse_starlette.sse import EventSourceResponse
from apps.api.src.services.orchestrator import ProductOrchestrator
from apps.api.src.core.security import get_current_user
from apps.api.src.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_orchestrator(request: Request) -> ProductOrchestrator:
    # Assume sentiment_service is in app.state
    sentiment_service = request.app.state.sentiment_service
    return ProductOrchestrator(sentiment_service=sentiment_service)

@router.get("/product/{asin}/stream", tags=["product"])
async def stream_product(
    asin: str,
    title: str = Query(..., description="Product title for search"),
    orchestrator: ProductOrchestrator = Depends(get_orchestrator),
    user_id: str = Depends(get_current_user)
):
    """Stream product analysis via SSE.
    
    Requires Bearer token authentication (currently stubbed).
    Streams partial results as crawlers complete, followed by sentiment and final verdict.
    """
    # Check rate limit
    from apps.api.src.services.rate_limiter import check_rate_limit
    await check_rate_limit(user_id)
    
    logger.info(f"User {user_id} requested stream for ASIN: {asin}")
    
    config = {
        "REDDIT_CLIENT_ID": settings.REDDIT_CLIENT_ID,
        "REDDIT_CLIENT_SECRET": settings.REDDIT_CLIENT_SECRET,
        "YOUTUBE_API_KEY": settings.YOUTUBE_API_KEY,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    }
    
    async def event_generator():
        try:
            async for event in orchestrator.stream_analysis(asin, title, config):
                yield {"data": json.dumps(event)}
        except Exception as e:
            logger.error(f"Error in event generator: {e}")
            yield {"data": json.dumps({"type": "error", "message": "Internal error in stream"})}
            
    return EventSourceResponse(event_generator())
