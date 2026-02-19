"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.ingestion.base import CacheManager
from src.storage.repository import Database

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

    # Redis cache (non-fatal)
    cache = CacheManager()
    try:
        await cache.connect()
        logger.info("Connected to Redis cache")
    except Exception:
        logger.warning("Redis unavailable — caching disabled", exc_info=True)

    # Database
    db = Database()
    try:
        await db.connect()
        await db.create_tables()
        logger.info("Connected to database")
    except Exception:
        logger.warning("Database connection failed", exc_info=True)

    # ChromaDB (non-fatal)
    try:
        from src.ingestion.tier3_research.vector_store import VectorStore
        VectorStore.get_client()
        logger.info("ChromaDB initialised")
    except Exception:
        logger.warning("ChromaDB init failed — RAG features unavailable", exc_info=True)

    # Seed default prompt templates
    try:
        from src.api.routers.templates import seed_defaults
        await seed_defaults()
    except Exception:
        logger.warning("Prompt template seeding failed", exc_info=True)

    yield

    # Shutdown
    logger.info("Shutting down MarketView API...")
    try:
        from src.ingestion.tier3_research.vector_store import VectorStore as _VS
        _VS.shutdown()
    except Exception:
        pass
    try:
        await db.disconnect()
    except Exception:
        pass
    try:
        await cache.disconnect()
    except Exception:
        pass
    logger.info("MarketView API shut down")


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
from src.api.routers import data, health, market, reddit, reports, sources, templates

app.include_router(health.router, tags=["Health"])
app.include_router(data.router, prefix="/api/v1/data", tags=["Data"])
app.include_router(market.router, prefix="/api/v1/data/market", tags=["Market Data"])
app.include_router(reddit.router, prefix="/api/v1/reddit", tags=["Reddit Sentiment"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(sources.router, prefix="/api/v1/sources", tags=["Sources"])
app.include_router(templates.router, prefix="/api/v1/templates", tags=["Templates"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "MarketView API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "disabled",
    }
