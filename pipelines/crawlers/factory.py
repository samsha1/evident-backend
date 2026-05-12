from pipelines.crawlers.core.crawler import PlatformCrawler
from pipelines.crawlers.platforms.reddit import RedditJsonParser, RedditStrategy
from pipelines.crawlers.platforms.youtube import YouTubeApiParser, YouTubeStrategy
from pipelines.crawlers.platforms.amazon import AmazonHtmlParser, AmazonStrategy

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
        
    # YouTube Crawler
    youtube_api_key = config.get("YOUTUBE_API_KEY")
    if youtube_api_key:
        strategy = YouTubeStrategy(api_key=youtube_api_key)
        parser = YouTubeApiParser()
        crawler = PlatformCrawler(strategy=strategy, parser=parser)
        crawlers.append(crawler)
        
    # Amazon Crawler (Scraping, no API key required for now)
    strategy = AmazonStrategy()
    parser = AmazonHtmlParser()
    crawler = PlatformCrawler(strategy=strategy, parser=parser)
    crawlers.append(crawler)
        
    return crawlers

