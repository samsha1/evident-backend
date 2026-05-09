from pydantic import BaseModel

class CrawlRequest(BaseModel):
    product_id: str
    platform: str
