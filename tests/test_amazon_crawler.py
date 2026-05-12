import pytest
from pipelines.crawlers.platforms.amazon import AmazonHtmlParser

def test_amazon_parser():
    """Test parsing Amazon HTML."""
    parser = AmazonHtmlParser()
    sample_html = """
    <div>
      <span class="a-profile-name">User One</span>
      <span data-hook="review-date">Reviewed in the United States on January 1, 2023</span>
      <span data-hook="review-body">This product is great!</span>
    </div>
    <div>
      <span class="a-profile-name">User Two</span>
      <span data-hook="review-date">Reviewed in the United States on January 2, 2023</span>
      <span data-hook="review-body">Terrible product.</span>
    </div>
    """
    reviews = parser.parse(sample_html)
    assert len(reviews) == 2
    assert reviews[0].content == "This product is great!"
    assert reviews[0].author == "User One"
    assert reviews[0].source == "amazon"
    assert reviews[1].content == "Terrible product."
    assert reviews[1].author == "User Two"
