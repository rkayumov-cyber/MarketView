"""Celery tasks for data management."""

import asyncio
import logging
from datetime import datetime

from celery import shared_task

from src.ingestion.aggregator import DataAggregator
from src.ingestion.base import CacheManager

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(name="src.tasks.data_tasks.refresh_market_data")
def refresh_market_data() -> dict:
    """Refresh all market data caches.

    This task is typically scheduled to run periodically during market hours.
    """
    logger.info("Refreshing market data cache")

    async def _refresh():
        aggregator = DataAggregator()

        # Get quick snapshot to refresh core data
        snapshot = await aggregator.get_quick_snapshot()

        return {
            "timestamp": snapshot.get("timestamp"),
            "status": "refreshed",
        }

    try:
        result = run_async(_refresh())
        logger.info(f"Market data refreshed at {result['timestamp']}")
        return result

    except Exception as e:
        logger.error(f"Market data refresh failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task(name="src.tasks.data_tasks.clear_old_cache")
def clear_old_cache() -> dict:
    """Clear old cache entries.

    This task is typically scheduled to run daily at midnight.
    """
    logger.info("Clearing old cache entries")

    async def _clear():
        cache = CacheManager()
        await cache.connect()

        # Clear old entries by prefix
        prefixes = ["fred", "reddit", "crypto", "equity", "fx", "commodity"]
        cleared = 0

        for prefix in prefixes:
            count = await cache.clear_prefix(prefix)
            cleared += count

        return cleared

    try:
        cleared = run_async(_clear())
        logger.info(f"Cleared {cleared} cache entries")
        return {
            "status": "completed",
            "entries_cleared": cleared,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task(name="src.tasks.data_tasks.health_check_sources")
def health_check_sources() -> dict:
    """Check health of all data sources."""
    logger.info("Running data source health checks")

    async def _check():
        aggregator = DataAggregator()
        return await aggregator.health_check_all()

    try:
        health = run_async(_check())
        all_healthy = all(health.values())

        return {
            "status": "healthy" if all_healthy else "degraded",
            "sources": health,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task(name="src.tasks.data_tasks.fetch_full_snapshot")
def fetch_full_snapshot() -> dict:
    """Fetch a complete market snapshot.

    This is useful for on-demand data refresh or before report generation.
    """
    logger.info("Fetching full market snapshot")

    async def _fetch():
        aggregator = DataAggregator()
        snapshot = await aggregator.get_full_snapshot()
        return snapshot.to_dict()

    try:
        result = run_async(_fetch())
        logger.info(f"Full snapshot fetched at {result['timestamp']}")
        return {
            "status": "completed",
            "timestamp": result["timestamp"],
            "errors": result.get("errors", []),
        }

    except Exception as e:
        logger.error(f"Full snapshot fetch failed: {e}")
        return {"status": "failed", "error": str(e)}
