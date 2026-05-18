"""
YouTube crawler backed by the Apify `streamers/youtube-scraper` Actor.

Actor docs: https://apify.com/streamers/youtube-scraper
Input reference (relevant fields):
    searchQuery  - keyword search string
    maxResults   - max videos to retrieve
    commentsScrape - whether to scrape comments
    maxComments  - max comments per video

Output items include:
    id, title, text (description), commentsCount, comments[].text/authorText/date
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from pipelines.crawlers.core.base import PlatformParser, RawReview
from pipelines.crawlers.strategies.apify import ApifyStrategy

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Apify Actor ID
# --------------------------------------------------------------------------
_ACTOR_ID = "streamers/youtube-scraper"

# Limits — keep costs reasonable for MVP
_MAX_VIDEOS = 5
_MAX_COMMENTS_PER_VIDEO = 30


# --------------------------------------------------------------------------
# Strategy — builds actor input from the product search query
# --------------------------------------------------------------------------

class YouTubeApifyStrategy(ApifyStrategy):
    """Runs the `streamers/youtube-scraper` Apify Actor."""

    actor_id = _ACTOR_ID

    def __init__(self, api_token: str):
        # youtube-scraper is typically fast (<2 min for small inputs)
        super().__init__(api_token=api_token, use_async=False)

    def build_input(self, query: str) -> dict:
        return {
            "searchQuery": query,
            "maxResults": _MAX_VIDEOS,
            "commentsScrape": True,
            "maxComments": _MAX_COMMENTS_PER_VIDEO,
        }


# --------------------------------------------------------------------------
# Parser — maps Apify dataset items → RawReview
# --------------------------------------------------------------------------

class YouTubeApifyParser(PlatformParser):
    """
    Parses `streamers/youtube-scraper` dataset items into RawReview objects.

    Each item may contain:
      - A video-level 'text' / 'description' (we include it as a review)
      - A 'comments' list with per-comment data
    """

    def parse(self, raw_data: str) -> list[RawReview]:
        try:
            items: list[dict] = json.loads(raw_data)
        except json.JSONDecodeError:
            logger.error("[YouTube] Failed to decode Apify response JSON")
            return []

        reviews: list[RawReview] = []

        for item in items:
            video_id: str = item.get("id") or item.get("videoId") or ""
            video_url: str = item.get("url") or (
                f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
            )

            # --- Comments (primary review signals) -----------------------
            comments: list[dict] = item.get("comments") or []
            for comment in comments:
                text = (comment.get("text") or "").strip()
                if not text:
                    continue

                author = comment.get("authorText") or comment.get("author") or "Anonymous"
                comment_id = comment.get("id") or f"{video_id}_{len(reviews)}"
                posted_at = _parse_yt_date(comment.get("publishedAt") or comment.get("date"))

                reviews.append(
                    RawReview(
                        source="youtube",
                        source_id=comment_id,
                        content=text,
                        author=author,
                        posted_at=posted_at,
                        metadata={
                            "video_url": video_url,
                            "video_id": video_id,
                            "video_title": item.get("title", ""),
                        },
                    )
                )

            # --- Video description as supplemental context ---------------
            description = (item.get("text") or item.get("description") or "").strip()
            if description and len(description) > 50:
                reviews.append(
                    RawReview(
                        source="youtube",
                        source_id=f"desc_{video_id}",
                        content=description,
                        author=item.get("channelName") or "Channel",
                        posted_at=_parse_yt_date(item.get("date")),
                        metadata={
                            "video_url": video_url,
                            "video_id": video_id,
                            "video_title": item.get("title", ""),
                            "type": "description",
                        },
                    )
                )

        logger.info(f"[YouTube] Parsed {len(reviews)} reviews from {len(items)} videos")
        return reviews


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _parse_yt_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
