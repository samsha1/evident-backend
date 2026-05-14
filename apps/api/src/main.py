import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.src.core.config import settings
from apps.api.src.routers import health, product, auth, products, reviews, crawl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("evident")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    logger.info("Starting Evident API (env=%s)", settings.APP_ENV)
    
    # Load sentiment model at startup
    from pipelines.sentiment.provider import LocalTransformerProvider, LlmApiProvider
    from pipelines.sentiment.service import SentimentService
    
    primary = LocalTransformerProvider(model_name=settings.SENTIMENT_MODEL_NAME)
    try:
        # Load the model eagerly to avoid latency on first request
        primary.load()
    except Exception as e:
        logger.error(f"Failed to load local sentiment model: {e}. Fallback will be used.")
        
    fallback = LlmApiProvider(api_key=settings.OPENAI_API_KEY)
    app.state.sentiment_service = SentimentService(primary=primary, fallback=fallback)
    
    yield
    logger.info("Shutting down Evident API")


app = FastAPI(
    title="Evident API",
    version="0.1.0",
    description="Cross-platform product review aggregator",
    lifespan=lifespan,
)

# CORS — allow Chrome extension and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(product.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(crawl.router, prefix="/api/v1")

