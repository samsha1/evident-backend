from fastapi import APIRouter
from packages.shared.schemas.crawl import CrawlRequest
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crawl", tags=["crawl"])

@router.post("/trigger")
async def trigger_crawl(request: CrawlRequest):
    # Log the job (enqueue logic stub)
    logger.info(f"Enqueued crawl job for product_id: {request.product_id} on platform: {request.platform}")
    return {"message": "Crawl job enqueued", "job_id": "stub-job-id"}
