from pipelines.crawlers.core.crawler import PlatformCrawler
from pipelines.crawlers.platforms.reddit import RedditJsonParser, RedditStrategy

def build_crawlers(config: dict[str, str]) -> list[PlatformCrawler]:
    """Build list of crawlers based on configuration dictionary.
    
    Args:
        config: Dictionary containing API keys and settings.
    """
    crawlers = []
    
    # Reddit Crawler
    reddit_client_id = config.get("REDDIT_CLIENT_ID")
    reddit_client_secret = config.get("REDDIT_CLIENT_SECRET")
    reddit_user_agent = config.get("REDDIT_USER_AGENT", "EvidentCrawler/0.1")
    
    if reddit_client_id and reddit_client_secret:
        strategy = RedditStrategy(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent
        )
        parser = RedditJsonParser()
        crawler = PlatformCrawler(strategy=strategy, parser=parser)
        crawlers.append(crawler)
        
    return crawlers
