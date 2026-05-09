from fastapi import FastAPI
from apps.api.src.routers import health, products, reviews, crawl
from mangum import Mangum
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ReviewAgg API", version="0.1.0")

app.include_router(health.router)
app.include_router(products.router)
app.include_router(reviews.router)
app.include_router(crawl.router)

@app.on_event("startup")
async def startup_event():
    logging.info("Starting up ReviewAgg API...")

handler = Mangum(app)
