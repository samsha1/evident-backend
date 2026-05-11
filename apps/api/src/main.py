import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.src.core.config import settings
from apps.api.src.routers import health

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("evident")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    logger.info("Starting Evident API (env=%s)", settings.APP_ENV)
    # TODO Phase 4: Load sentiment model here
    yield
    logger.info("Shutting down Evident API")
    # TODO: Close Redis, DB engine on shutdown


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
# TODO Phase 5: Add auth, product routers
