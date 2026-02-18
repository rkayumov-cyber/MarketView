"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.ingestion.base import CacheManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting MarketView API...")
    cache = CacheManager()
    await cache.connect()
    logger.info("Connected to Redis cache")

    yield

    # Shutdown
    logger.info("Shutting down MarketView API...")
    await cache.disconnect()
    logger.info("Disconnected from Redis cache")


app = FastAPI(
    title="MarketView API",
    description="Institutional-grade Market Analysis System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from src.api.routers import data, health, reports

app.include_router(health.router, tags=["Health"])
app.include_router(data.router, prefix="/api/v1/data", tags=["Data"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "MarketView API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "disabled",
    }
