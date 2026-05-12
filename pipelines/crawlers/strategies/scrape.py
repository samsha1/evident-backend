from pipelines.crawlers.core.base import CrawlStrategy
import aiohttp
import logging

logger = logging.getLogger(__name__)

class AiohttpScrapeStrategy(CrawlStrategy):
    """Strategy for scraping HTML content using aiohttp.
    
    Expects the full URL to be passed as the query or in kwargs.
    """
    
    def __init__(self, headers: dict[str, str] | None = None):
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        
    async def fetch(self, query: str, **kwargs) -> str:
        """Fetch HTML content from a URL.
        
        Args:
            query: The URL to fetch (or ASIN if built by a subclass).
            kwargs: May contain 'url' to override query.
        """
        url = kwargs.get("url", query)
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch {url}: {resp.status}")
                        return f"Error: {resp.status}"
                    return await resp.text()
            except Exception as e:
                logger.error(f"Exception fetching {url}: {e}")
                return f"Error: {str(e)}"
