"""
Reddit crawler backed by the Apify `trudax/reddit-scraper-lite` Actor.

Actor docs: https://apify.com/trudax/reddit-scraper-lite
Input reference (relevant fields):
    searches        - list of search strings
    type            - "posts" | "comments"
    maxItems        - total items to retrieve
    sort            - "relevance" | "top" | "new"
    time            - "all" | "year" | "month" | "week" | "day"
    includeComments - whether to include comments in post results

Output items include:
    id, title, body/selftext, author, created_utc, url, subreddit, score
    For comment-type: id, body, author, created_utc, url, subreddit
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
_ACTOR_ID = "trudax/reddit-scraper-lite"

# Limits
_MAX_ITEMS = 50


# --------------------------------------------------------------------------
# Strategy — builds actor input from the product search query
# --------------------------------------------------------------------------

class RedditApifyStrategy(ApifyStrategy):
    """Runs the `trudax/reddit-scraper-lite` Apify Actor."""

    actor_id = _ACTOR_ID

    def __init__(self, api_token: str):
        # Reddit scraper is generally fast for small item counts
        super().__init__(api_token=api_token, use_async=False)

    def build_input(self, query: str) -> dict:
        return {
            "searches": [query],
            "type": "posts",
            "maxItems": _MAX_ITEMS,
            "sort": "relevance",
            "time": "all",
            "includeComments": True,
        }


# --------------------------------------------------------------------------
# Parser — maps Apify dataset items → RawReview
# --------------------------------------------------------------------------

class RedditApifyParser(PlatformParser):
    """
    Parses `trudax/reddit-scraper-lite` dataset items into RawReview objects.

    Each item represents a Reddit post. When `includeComments=True` the actor
    nests comment objects inside `item["comments"]`.
    """

    def parse(self, raw_data: str) -> list[RawReview]:
        try:
            items: list[dict] = json.loads(raw_data)
        except json.JSONDecodeError:
            logger.error("[Reddit] Failed to decode Apify response JSON")
            return []

        reviews: list[RawReview] = []

        for item in items:
            post_id = item.get("id") or ""
            post_url = item.get("url") or ""
            author = item.get("author") or "Anonymous"
            subreddit = item.get("subreddit") or ""
            posted_at = _parse_unix(item.get("created_utc"))

            # --- Post body (selftext or title) ---------------------------
            body = (item.get("body") or item.get("selftext") or "").strip()
            title = (item.get("title") or "").strip()

            # Prefer body+title combo; fall back to title-only
            if body:
                content = f"{title}\n\n{body}" if title else body
            elif title:
                content = title
            else:
                content = ""

            if content:
                reviews.append(
                    RawReview(
                        source="reddit",
                        source_id=post_id,
                        content=content,
                        author=author,
                        posted_at=posted_at,
                        metadata={
                            "url": post_url,
                            "subreddit": subreddit,
                            "score": str(item.get("score", 0)),
                        },
                    )
                )

            # --- Nested comments ------------------------------------------
            for comment in item.get("comments") or []:
                c_body = (comment.get("body") or "").strip()
                if not c_body:
                    continue

                c_id = comment.get("id") or f"{post_id}_c{len(reviews)}"
                c_author = comment.get("author") or "Anonymous"
                c_at = _parse_unix(comment.get("created_utc"))

                reviews.append(
                    RawReview(
                        source="reddit",
                        source_id=c_id,
                        content=c_body,
                        author=c_author,
                        posted_at=c_at,
                        metadata={
                            "url": post_url,
                            "subreddit": subreddit,
                            "parent_post_id": post_id,
                        },
                    )
                )

        logger.info(f"[Reddit] Parsed {len(reviews)} items from {len(items)} posts")
        return reviews


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _parse_unix(ts: int | float | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, OSError):
        return None
