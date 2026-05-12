import asyncio
from asyncio import Queue
from pipelines.crawlers.core.base import CrawlStrategy, PlatformParser, CrawlerResult

class PlatformCrawler:
    """Combines a strategy and a parser to crawl a platform."""
    
    def __init__(self, source: str, strategy: CrawlStrategy, parser: PlatformParser, timeout: float = 30.0):
        self.source = source
        self.strategy = strategy
        self.parser = parser
        self.timeout = timeout

    async def run(
        self, 
        query: str, 
        queue: Queue[CrawlerResult] | None = None,
        **kwargs: object
    ) -> CrawlerResult:
        """Run the crawler for a query.
        
        Args:
            query: The search query or ASIN.
            queue: Optional asyncio Queue to push results to.
            kwargs: Additional arguments for the strategy.
        """
        try:
            raw_data = await asyncio.wait_for(
                self.strategy.fetch(query, **kwargs), 
                timeout=self.timeout
            )
            reviews = self.parser.parse(raw_data)
            
            result = CrawlerResult(source=self.source, reviews=reviews)
            
            if queue is not None:
                await queue.put(result)
                
            return result
        except asyncio.TimeoutError:
            print(f"Crawler timed out after {self.timeout}s for query: {query}")
            result = CrawlerResult(
                source=self.source,
                reviews=[], 
                metadata={"error": "timeout", "query": query}
            )
            if queue is not None:
                await queue.put(result)
            return result
        except Exception as e:
            print(f"Crawler error: {e} for query: {query}")
            result = CrawlerResult(
                source=self.source,
                reviews=[], 
                metadata={"error": str(e), "query": query}
            )
            if queue is not None:
                await queue.put(result)
            return result
