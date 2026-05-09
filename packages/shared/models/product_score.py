from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from packages.shared.models.base import Base

class ProductScore(Base):
    __tablename__ = "product_scores"

    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.product_id"), primary_key=True)
    overall_sentiment: Mapped[float] = mapped_column(Float)
    verdict: Mapped[str] = mapped_column(String)
    total_reviews: Mapped[int] = mapped_column(Integer)
    platform_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    top_pros: Mapped[list[str]] = mapped_column(JSON, default=list)
    top_cons: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
