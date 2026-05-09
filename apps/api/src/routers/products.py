from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.src.core.database import get_db
from packages.shared.schemas.product import ProductResponse
from apps.api.src.services.cache import get_product_cache, set_product_cache
from typing import List

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    cached = await get_product_cache(product_id)
    if cached:
        return cached

    # Stub response
    mock_product = {
        "product_id": product_id,
        "asin": "B08N5WRWNW",
        "name": "Apple MacBook Air M1",
        "brand": "Apple",
        "category": "Electronics",
        "upc": "194252055694",
        "platform_refs": {},
        "created_at": "2026-05-09T00:00:00Z",
        "last_crawled_at": None
    }
    
    await set_product_cache(product_id, mock_product)
    return mock_product
