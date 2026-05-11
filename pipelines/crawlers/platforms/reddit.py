from datetime import datetime, timezone
import json
import aiohttp
from pipelines.crawlers.core.base import PlatformParser, RawReview, CrawlStrategy

class RedditJsonParser(PlatformParser):
    """Parses Reddit JSON API responses."""
    
    def parse(self, raw_data: str) -> list[RawReview]:
        """Parse raw JSON string from Reddit into RawReview objects."""
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            print("Failed to decode Reddit JSON")
            return []
            
        reviews = []
        
        # Reddit listings usually have data -> children
        if isinstance(data, dict) and "data" in data and "children" in data["data"]:
            children = data["data"]["children"]
            for child in children:
                item_data = child.get("data", {})
                
                # Extract title + selftext for posts, or body for comments
                content = item_data.get("selftext") or item_data.get("body") or item_data.get("title")
                if not content:
                    continue
                    
                # If both title and selftext exist, combine them
                if item_data.get("title") and item_data.get("selftext"):
                    content = f"{item_data['title']}\n\n{item_data['selftext']}"
                    
                source_id = item_data.get("id", "")
                author = item_data.get("author")
                
                created_utc = item_data.get("created_utc")
                posted_at = None
                if created_utc:
                    # Python 3.12 compliant
                    posted_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                    
                reviews.append(
                    RawReview(
                        source="reddit",
                        source_id=source_id,
                        content=content,
                        author=author,
                        posted_at=posted_at
                    )
                )
                
        return reviews

class RedditStrategy(CrawlStrategy):
    """Strategy for fetching data from Reddit API with OAuth2."""
    
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.token = None
        
    async def _get_token(self) -> str:
        """Get Reddit OAuth2 token."""
        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        headers = {"User-Agent": self.user_agent}
        data = {"grant_type": "client_credentials"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                headers=headers,
                data=data
            ) as response:
                response.raise_for_status()
                res_data = await response.json()
                return str(res_data["access_token"])
                
    async def fetch(self, query: str, **kwargs: object) -> str:
        """Fetch data from Reddit search."""
        if not self.token:
            self.token = await self._get_token()
            
        headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": self.user_agent
        }
        
        # Reddit search endpoint
        url = f"https://oauth.reddit.com/search.json?q={query}&limit=10"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 401:
                    # Token might have expired, try once more
                    self.token = await self._get_token()
                    headers["Authorization"] = f"Bearer {self.token}"
                    async with session.get(url, headers=headers) as retry_response:
                        retry_response.raise_for_status()
                        return await retry_response.text()
                
                response.raise_for_status()
                return await response.text()
