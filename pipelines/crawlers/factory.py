"""
Crawler factory — assembles platform crawlers from runtime config.

Priority:
  1. YouTube   — Apify streamers/youtube-scraper  (needs APIFY_TOKEN)
  2. Reddit    — Apify trudax/reddit-scraper-lite  (needs APIFY_TOKEN)
  3. Amazon    — custom HTML scraper               (no API key required)

To add a new platform simply import its Strategy/Parser pair and add a
block following the same pattern below.
"""

import logging
from pipelines.crawlers.core.crawler import PlatformCrawler

# Apify-backed platforms
from pipelines.crawlers.platforms.youtube import YouTubeApifyStrategy, YouTubeApifyParser
from pipelines.crawlers.platforms.reddit import RedditApifyStrategy, RedditApifyParser

# Custom scraper (untouched)
from pipelines.crawlers.platforms.amazon import AmazonHtmlParser, AmazonStrategy

logger = logging.getLogger(__name__)


def build_crawlers(config: dict[str, str]) -> list[PlatformCrawler]:
    """Build active crawlers from the supplied configuration dict.

    Args:
        config: Flat key-value map of environment/settings values.
                Expected keys:
                  APIFY_TOKEN        — enables YouTube + Reddit via Apify
                  (no key needed)    — Amazon always included

    Returns:
        List of PlatformCrawler instances ready to run concurrently.
    """
    crawlers: list[PlatformCrawler] = []
    apify_token: str | None = config.get("APIFY_TOKEN")

    # ------------------------------------------------------------------
    # YouTube  (Apify)
    # ------------------------------------------------------------------
    if apify_token:
        strategy = YouTubeApifyStrategy(api_token=apify_token)
        parser = YouTubeApifyParser()
        crawlers.append(
            PlatformCrawler(
                source="youtube",
                strategy=strategy,
                parser=parser,
                timeout=300.0,  # Actor can take up to ~3 min
            )
        )
        logger.info("[Factory] YouTube crawler enabled (Apify)")
    else:
        logger.warning("[Factory] APIFY_TOKEN not set — YouTube crawler disabled")

    # ------------------------------------------------------------------
    # Reddit  (Apify)
    # ------------------------------------------------------------------
    if apify_token:
        strategy = RedditApifyStrategy(api_token=apify_token)
        parser = RedditApifyParser()
        crawlers.append(
            PlatformCrawler(
                source="reddit",
                strategy=strategy,
                parser=parser,
                timeout=120.0,
            )
        )
        logger.info("[Factory] Reddit crawler enabled (Apify)")
    else:
        logger.warning("[Factory] APIFY_TOKEN not set — Reddit crawler disabled")

    # ------------------------------------------------------------------
    # Amazon  (custom HTML scraper — unchanged)
    # ------------------------------------------------------------------
    strategy = AmazonStrategy()
    parser = AmazonHtmlParser()
    crawlers.append(
        PlatformCrawler(
            source="amazon",
            strategy=strategy,
            parser=parser,
            timeout=30.0,
        )
    )
    logger.info("[Factory] Amazon crawler enabled (HTML scraper)")

    logger.info(f"[Factory] Total crawlers built: {len(crawlers)}")
    return crawlers
