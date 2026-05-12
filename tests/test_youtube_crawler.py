import pytest
from pipelines.crawlers.platforms.youtube import YouTubeApiParser

def test_youtube_parser():
    """Test parsing YouTube JSON."""
    parser = YouTubeApiParser()
    sample_json = """
    {
      "items": [
        {
          "id": "comment1",
          "snippet": {
            "topLevelComment": {
              "snippet": {
                "textDisplay": "Great video",
                "authorDisplayName": "user1",
                "publishedAt": "2023-01-01T00:00:00Z"
              }
            }
          }
        }
      ]
    }
    """
    reviews = parser.parse(sample_json)
    assert len(reviews) == 1
    assert reviews[0].source_id == "comment1"
    assert reviews[0].content == "Great video"
    assert reviews[0].author == "user1"
    assert reviews[0].source == "youtube"
