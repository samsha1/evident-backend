from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ProductBase(BaseModel):
    asin: str
    name: str
    brand: str
    category: str
    upc: Optional[str] = None
    platform_refs: dict = {}

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    product_id: str
    created_at: datetime
    last_crawled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
