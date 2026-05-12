from datetime import datetime
import logging
import re
from pipelines.crawlers.core.base import PlatformParser, RawReview
from pipelines.crawlers.strategies.scrape import AiohttpScrapeStrategy

logger = logging.getLogger(__name__)

class AmazonStrategy(AiohttpScrapeStrategy):
    """Strategy for Amazon that builds the review URL from ASIN."""
    
    async def fetch(self, query: str, **kwargs) -> str:
        """Fetch reviews for an ASIN.
        
        Args:
            query: The ASIN of the product.
        """
        # Build Amazon review URL
        url = f"https://www.amazon.com/product-reviews/{query}"
        logger.info(f"Fetching Amazon reviews from {url}")
        return await super().fetch(url, **kwargs)

class AmazonHtmlParser(PlatformParser):
    """Parser for Amazon product reviews HTML using regex."""
    
    def parse(self, raw_data: str) -> list[RawReview]:
        reviews = []
        
        # Simple regex to find review blocks
        # This is a fallback approach since BeautifulSoup is not available.
        # It looks for review bodies with data-hook="review-body"
        
        # Find review bodies
        bodies = re.findall(r'<span[^>]*data-hook="review-body"[^>]*>(.*?)</span>', raw_data, re.DOTALL)
        
        # Find authors
        authors = re.findall(r'<span class="a-profile-name">(.*?)</span>', raw_data)
        
        # Find dates
        dates = re.findall(r'<span[^>]*data-hook="review-date"[^>]*>(.*?)</span>', raw_data)
        
        # Clean up HTML tags from content
        def clean_html(text: str) -> str:
            # Remove HTML tags
            cleaned = re.sub(r'<[^>]+>', '', text)
            # Replace common HTML entities
            cleaned = cleaned.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
            return cleaned.strip()
            
        min_len = min(len(bodies), len(authors))
        
        for i in range(min_len):
            content = clean_html(bodies[i])
            author = clean_html(authors[i])
            
            # Extract date if available
            posted_at = None
            if i < len(dates):
                date_str = clean_html(dates[i])
                # Date format is often "Reviewed in the United States on January 1, 2023"
                match = re.search(r'on\s+([A-Za-z]+\s+\d+,\s+\d+)', date_str)
                if match:
                    try:
                        posted_at = datetime.strptime(match.group(1), "%B %d, %Y")
                    except ValueError:
                        pass
                        
            reviews.append(
                RawReview(
                    source="amazon",
                    source_id=f"scraped_{i}",  # Fallback ID
                    content=content,
                    author=author,
                    posted_at=posted_at,
                )
            )
            
        logger.info(f"Parsed {len(reviews)} reviews from Amazon HTML")
        return reviews
