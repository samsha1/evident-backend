import pytest
from unittest.mock import AsyncMock, MagicMock
from pipelines.crawlers.platforms.reddit import RedditJsonParser
from pipelines.crawlers.core.crawler import PlatformCrawler

def test_reddit_parser():
    """Test parsing Reddit JSON."""
    parser = RedditJsonParser()
    sample_json = """
    {
      "kind": "Listing",
      "data": {
        "children": [
          {
            "kind": "t3",
            "data": {
              "id": "123",
              "title": "Test Title",
              "selftext": "Test Body",
              "author": "user1",
              "created_utc": 1672531200
            }
          }
        ]
      }
    }
    """
    reviews = parser.parse(sample_json)
    assert len(reviews) == 1
    assert reviews[0].source_id == "123"
    assert reviews[0].content == "Test Title\n\nTest Body"
    assert reviews[0].author == "user1"
    assert reviews[0].source == "reddit"

@pytest.mark.asyncio
async def test_crawler_with_mock_strategy():
    """Test PlatformCrawler with a mocked strategy."""
    mock_strategy = MagicMock()
    mock_strategy.fetch = AsyncMock(return_value='{"data": {"children": []}}')
    
    parser = RedditJsonParser()
    crawler = PlatformCrawler(source="reddit", strategy=mock_strategy, parser=parser)
    
    result = await crawler.run("test_query")
    
    assert result.reviews == []
    mock_strategy.fetch.assert_called_once_with("test_query")
