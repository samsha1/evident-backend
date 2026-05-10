from fastapi import FastAPI
from apps.api.src.routers import health, products, reviews, crawl
from mangum import Mangum
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Evident API", version="0.1.0")

from fastapi import APIRouter

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(products.router)
api_router.include_router(reviews.router)
api_router.include_router(crawl.router)

app.include_router(api_router)
@app.on_event("startup")
async def startup_event():
    logging.info("Starting up Evident API...")

handler = Mangum(app)
