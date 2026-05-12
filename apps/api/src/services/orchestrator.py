import asyncio
from asyncio import Queue
import logging
from typing import AsyncGenerator
from pipelines.crawlers.factory import build_crawlers
from pipelines.crawlers.core.base import CrawlerResult, RawReview
from pipelines.sentiment.service import SentimentService
from pipelines.verdict import compute_verdict, VerdictInput

logger = logging.getLogger(__name__)

class ProductOrchestrator:
    """Orchestrates the hot-path: crawling, sentiment analysis, and verdict computation."""
    
    def __init__(self, sentiment_service: SentimentService):
        self.sentiment_service = sentiment_service

    async def stream_analysis(
        self, asin: str, title: str, config: dict[str, str]
    ) -> AsyncGenerator[dict, None]:
        """Crawl reviews, analyze sentiment, and stream results via SSE.
        
        Handles cache check and distributed locks.
        """
        from apps.api.src.services.cache import (
            get_product_cache, set_product_cache, 
            acquire_lock, release_lock, 
            publish_to_channel, subscribe_to_channel
        )
        import json
        
        # 1. Check cache
        cached_data, cache_status = await get_product_cache(asin)
        
        if cache_status == "fresh":
            logger.info(f"Cache hit (FRESH) for ASIN: {asin}")
            yield {"type": "cache_hit", "status": "fresh"}
            yield cached_data
            return
            
        elif cache_status == "stale":
            logger.info(f"Cache hit (STALE) for ASIN: {asin}")
            yield {"type": "cache_hit", "status": "stale"}
            yield cached_data
            
            # Trigger background refresh
            asyncio.create_task(self._background_refresh(asin, title, config))
            return
            
        # 2. MISS or no cache -> Try to acquire lock
        lock_acquired = await acquire_lock(asin)
        
        if not lock_acquired:
            logger.info(f"Lock active for {asin}, waiting for results...")
            yield {"type": "info", "message": "Another request is processing this product. Waiting..."}
            
            # Subscribe to channel to get results
            pubsub = await subscribe_to_channel(asin)
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        data = json.loads(message["data"])
                        yield data
                        if data.get("type") == "final":
                            return
            except Exception as e:
                logger.error(f"Error listening to channel: {e}")
            finally:
                await pubsub.unsubscribe()
                await pubsub.close()
            return
            
        # 3. Lock acquired -> Proceed with crawl
        logger.info(f"Lock acquired for {asin}. Proceeding with crawl.")
        try:
            async for event in self._do_stream_crawl_and_analyze(asin, title, config):
                yield event
                # Publish to channel for waiting requests
                await publish_to_channel(asin, event)
                
                # Cache final result
                if event.get("type") == "final" and event.get("verdict") != "UNAVAILABLE":
                    await set_product_cache(asin, event)
        finally:
            await release_lock(asin)

    async def _background_refresh(self, asin: str, title: str, config: dict):
        """Background refresh for stale cache."""
        from apps.api.src.services.cache import acquire_lock, release_lock, set_product_cache
        
        lock_acquired = await acquire_lock(asin)
        if not lock_acquired:
            return
            
        logger.info(f"Starting background refresh for ASIN: {asin}")
        try:
            final_event = None
            async for event in self._do_stream_crawl_and_analyze(asin, title, config):
                if event.get("type") == "final":
                    final_event = event
                    
            if final_event and final_event.get("verdict") != "UNAVAILABLE":
                await set_product_cache(asin, final_event)
                logger.info(f"Background refresh complete for ASIN: {asin}")
        except Exception as e:
            logger.error(f"Error in background refresh for {asin}: {e}")
        finally:
            await release_lock(asin)

    async def _do_stream_crawl_and_analyze(
        self, asin: str, title: str, config: dict[str, str]
    ) -> AsyncGenerator[dict, None]:
        """Internal method to perform crawl and analysis, yielding events."""
        crawlers = build_crawlers(config)
        queue: Queue[CrawlerResult] = Queue()
        
        # Start crawlers concurrently
        tasks = []
        for crawler in crawlers:
            query = asin if crawler.source == "amazon" else title
            logger.info(f"Starting crawler for {crawler.source} with query: {query}")
            tasks.append(asyncio.create_task(crawler.run(query, queue=queue)))
            
        yield {"type": "info", "message": f"Started {len(crawlers)} crawlers"}
        
        pending_sources = {crawler.source for crawler in crawlers}
        all_reviews: list[RawReview] = []
        
        # Drain queue as results arrive
        while pending_sources:
            try:
                result: CrawlerResult = await asyncio.wait_for(queue.get(), timeout=15.0)
                queue.task_done()
                
                source = result.source
                if source in pending_sources:
                    pending_sources.remove(source)
                    
                status = result.metadata.get("error", "done")
                count = len(result.reviews)
                
                logger.info(f"Received results from {source}: {count} reviews, status: {status}")
                
                yield {
                    "type": "source_status",
                    "source": source,
                    "status": status,
                    "count": count
                }
                
                if result.reviews:
                    all_reviews.extend(result.reviews)
                    
            except asyncio.TimeoutError:
                logger.warning("Queue drain timed out waiting for remaining crawlers")
                yield {"type": "info", "message": "Some sources timed out"}
                break
                
        # Wait for all tasks to complete just in case
        await asyncio.gather(*tasks, return_exceptions=True)
        
        yield {"type": "info", "message": f"Crawling complete. Total reviews: {len(all_reviews)}"}
        
        if not all_reviews:
            yield {
                "type": "final",
                "verdict": "UNAVAILABLE",
                "confidence": 0.0,
                "summary": "No reviews found or all sources failed."
            }
            return
            
        # Process sentiment
        yield {"type": "info", "message": "Analyzing sentiment..."}
        
        logger.info(f"Analyzing sentiment for {len(all_reviews)} reviews")
        sentiment_tasks = [self.sentiment_service.analyze(r.content) for r in all_reviews]
        sentiment_results = await asyncio.gather(*sentiment_tasks)
        
        verdict_inputs = [
            VerdictInput(
                review_id=r.source_id,
                source=r.source,
                sentiment=s
            )
            for r, s in zip(all_reviews, sentiment_results)
        ]
        
        yield {"type": "info", "message": "Computing verdict..."}
        verdict_result = compute_verdict(verdict_inputs)
        
        yield {
            "type": "final",
            "verdict": verdict_result.verdict,
            "confidence": verdict_result.confidence,
            "positive_pct": verdict_result.positive_pct,
            "negative_pct": verdict_result.negative_pct,
            "neutral_pct": verdict_result.neutral_pct,
            "total_reviews": verdict_result.total_reviews,
            "sources_json": verdict_result.sources_json,
            "summary": f"Computed verdict from {verdict_result.total_reviews} reviews."
        }
