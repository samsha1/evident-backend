from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from packages.shared.models.base import Base
import uuid

class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.product_id"), index=True)
    platform: Mapped[str] = mapped_column(String, index=True)
    raw_text: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    upvotes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str] = mapped_column(String)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String, nullable=True)
