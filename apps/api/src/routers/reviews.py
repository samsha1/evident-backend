from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.src.core.database import get_db

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.get("/")
async def get_reviews(db: AsyncSession = Depends(get_db)):
    return []
