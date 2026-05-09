from pipelines.crawlers.base import BaseCrawler
from typing import List
from packages.shared.schemas.review import ReviewCreate

class YoutubeCrawler(BaseCrawler):
    platform = "youtube"

    async def crawl(self, product_id: str, query: str) -> List[ReviewCreate]:
        # Stub implementation
        return []
