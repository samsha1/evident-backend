from pipelines.crawlers.base import BaseCrawler
from typing import List
from packages.shared.schemas.review import ReviewCreate

class RedditCrawler(BaseCrawler):
    platform = "reddit"

    async def crawl(self, product_id: str, query: str) -> List[ReviewCreate]:
        # Stub implementation
        return []
