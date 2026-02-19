"""Reddit sentiment API endpoints with live/mock toggle."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query

from src.api.routers.market import DataSourceEnum
from src.data.mock_data import (
    get_mock_reddit_posts,
    get_mock_reddit_sentiment,
    get_mock_reddit_trending,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy singleton — only instantiated when live data is requested
_reddit_client = None


def _get_reddit_client():
    global _reddit_client
    if _reddit_client is None:
        from src.ingestion.tier2_sentiment.reddit_client import RedditClient

        _reddit_client = RedditClient()
    return _reddit_client


async def _fetch_with_fallback(
    source: DataSourceEnum,
    live_fn,
    mock_fn,
    label: str,
) -> dict[str, Any]:
    """Fetch live data or mock, with auto-fallback on live failure."""
    if source == DataSourceEnum.mock:
        return {
            "source": "mock",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": mock_fn(),
        }

    try:
        data = await live_fn()
        if data:
            return {
                "source": "live (reddit)",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": data,
            }
        raise ValueError(f"Empty data from live {label}")
    except Exception as e:
        logger.warning("Live %s fetch failed, falling back to mock: %s", label, e)
        return {
            "source": "mock (fallback)",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": mock_fn(),
        }


async def _live_sentiment() -> dict[str, Any]:
    client = _get_reddit_client()
    overall = await client.get_overall_sentiment()
    all_subs = await client.get_all_sentiment()
    return {
        "overall": overall,
        "subreddits": {k: v.to_dict() for k, v in all_subs.items()},
    }


async def _live_posts() -> dict[str, Any]:
    from src.config.constants import REDDIT_SUBREDDITS

    client = _get_reddit_client()
    all_posts = []
    for sub in REDDIT_SUBREDDITS:
        posts = await client.fetch_subreddit_posts(sub, limit=25, time_filter="day")
        all_posts.extend(p.to_dict() for p in posts)
    all_posts.sort(key=lambda p: p["score"], reverse=True)
    return {"posts": all_posts[:50]}


async def _live_trending() -> dict[str, Any]:
    client = _get_reddit_client()
    trending = await client.get_trending_tickers(20)
    return {
        "tickers": [{"symbol": sym, "mentions": cnt} for sym, cnt in trending],
    }


@router.get("/sentiment")
async def reddit_sentiment(
    source: DataSourceEnum = Query(DataSourceEnum.live, description="Data source"),
) -> dict[str, Any]:
    """Overall Reddit sentiment with per-subreddit breakdown."""
    return await _fetch_with_fallback(
        source, _live_sentiment, get_mock_reddit_sentiment, "reddit sentiment"
    )


@router.get("/posts")
async def reddit_posts(
    source: DataSourceEnum = Query(DataSourceEnum.live, description="Data source"),
) -> dict[str, Any]:
    """Hot Reddit posts across all monitored subreddits."""
    return await _fetch_with_fallback(
        source, _live_posts, get_mock_reddit_posts, "reddit posts"
    )


@router.get("/trending")
async def reddit_trending(
    source: DataSourceEnum = Query(DataSourceEnum.live, description="Data source"),
) -> dict[str, Any]:
    """Trending tickers by mention count across subreddits."""
    return await _fetch_with_fallback(
        source, _live_trending, get_mock_reddit_trending, "reddit trending"
    )
