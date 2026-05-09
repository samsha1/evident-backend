from abc import ABC, abstractmethod
from typing import List
from packages.shared.schemas.review import ReviewCreate

class BaseCrawler(ABC):
    platform: str
    delay_between_requests: float = 1.0

    @abstractmethod
    async def crawl(self, product_id: str, query: str) -> List[ReviewCreate]:
        """
        Crawl the platform for reviews.
        Must respect Retry-After headers and delay_between_requests.
        """
        pass
