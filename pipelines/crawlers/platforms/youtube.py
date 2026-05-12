from datetime import datetime, timezone
import json
import logging
from pipelines.crawlers.core.base import CrawlStrategy, PlatformParser, RawReview
import aiohttp

logger = logging.getLogger(__name__)

class YouTubeStrategy(CrawlStrategy):
    """Strategy for fetching YouTube comments using the Data API v3."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
    async def fetch(self, query: str, **kwargs) -> str:
        """Fetch comments for videos found by searching the query."""
        async with aiohttp.ClientSession() as session:
            # 1. Search for videos
            search_url = f"{self.base_url}/search"
            search_params = {
                "key": self.api_key,
                "q": query,
                "part": "snippet",
                "type": "video",
                "maxResults": 5,  # Limit for MVP
            }
            
            try:
                async with session.get(search_url, params=search_params) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"YouTube search failed: {error_text}")
                        return json.dumps({"error": "Search failed", "status": resp.status})
                    
                    search_data = await resp.json()
            except Exception as e:
                logger.error(f"YouTube search exception: {e}")
                return json.dumps({"error": str(e)})
                
            video_ids = [item["id"]["videoId"] for item in search_data.get("items", []) if "videoId" in item.get("id", {})]
            
            all_comments = []
            
            # 2. Fetch comment threads for each video
            for video_id in video_ids:
                comments_url = f"{self.base_url}/commentThreads"
                comments_params = {
                    "key": self.api_key,
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": 20,
                }
                
                try:
                    async with session.get(comments_url, params=comments_params) as resp:
                        if resp.status == 200:
                            comments_data = await resp.json()
                            all_comments.extend(comments_data.get("items", []))
                        else:
                            logger.warning(f"Failed to fetch comments for video {video_id}: {resp.status}")
                except Exception as e:
                    logger.warning(f"Exception fetching comments for video {video_id}: {e}")
                        
            return json.dumps({"items": all_comments})

class YouTubeApiParser(PlatformParser):
    """Parser for YouTube commentThreads API response."""
    
    def parse(self, raw_data: str) -> list[RawReview]:
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            logger.error("Failed to decode YouTube JSON")
            return []
            
        items = data.get("items", [])
        reviews = []
        
        for item in items:
            snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            content = snippet.get("textDisplay", "")
            author = snippet.get("authorDisplayName", "")
            published_at_str = snippet.get("publishedAt", "")
            
            posted_at = None
            if published_at_str:
                try:
                    # YouTube returns ISO 8601 strings
                    posted_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                except ValueError:
                    pass
                    
            reviews.append(
                RawReview(
                    source="youtube",
                    source_id=item.get("id", ""),
                    content=content,
                    author=author,
                    posted_at=posted_at,
                )
            )
            
        return reviews
