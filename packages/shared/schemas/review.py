from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ReviewBase(BaseModel):
    product_id: str
    platform: str
    raw_text: str
    author: str
    rating: Optional[float] = None
    upvotes: Optional[int] = None
    source_url: str
    crawled_at: datetime
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    review_id: str

    model_config = ConfigDict(from_attributes=True)
