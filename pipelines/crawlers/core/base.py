from datetime import datetime
from typing import Protocol, runtime_checkable
from pydantic import BaseModel, Field

class RawReview(BaseModel):
    """Normalized review data before insertion or processing."""
    source: str
    source_id: str
    content: str
    author: str | None = None
    posted_at: datetime | None = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

class CrawlerResult(BaseModel):
    """Result of a crawler execution."""
    reviews: list[RawReview]
    metadata: dict[str, str] = Field(default_factory=dict)

@runtime_checkable
class CrawlStrategy(Protocol):
    """Protocol for fetching data from a source."""
    async def fetch(self, query: str, **kwargs) -> str:
        """Fetch raw data from the source (returns JSON string or HTML)."""
        ...

@runtime_checkable
class PlatformParser(Protocol):
    """Protocol for parsing raw data from a specific platform."""
    def parse(self, raw_data: str) -> list[RawReview]:
        """Parse raw data into a list of RawReview objects."""
        ...
