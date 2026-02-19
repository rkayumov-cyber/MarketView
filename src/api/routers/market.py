"""Market data API endpoints with live/mock toggle."""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Query

from src.data.mock_data import (
    get_mock_commodities,
    get_mock_crypto,
    get_mock_equities,
    get_mock_fx,
    get_mock_snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class DataSourceEnum(str, Enum):
    live = "live"
    mock = "mock"


async def _live_snapshot() -> dict[str, Any]:
    from src.ingestion.aggregator import DataAggregator

    agg = DataAggregator()
    return await agg.get_quick_snapshot()


async def _live_equities() -> dict[str, Any]:
    from src.ingestion.aggregator import DataAggregator

    agg = DataAggregator()
    return await agg._fetch_equities()


async def _live_fx() -> dict[str, Any]:
    from src.ingestion.aggregator import DataAggregator

    agg = DataAggregator()
    return await agg._fetch_fx()


async def _live_commodities() -> dict[str, Any]:
    from src.ingestion.aggregator import DataAggregator

    agg = DataAggregator()
    return await agg._fetch_commodities()


async def _live_crypto() -> dict[str, Any]:
    from src.ingestion.aggregator import DataAggregator

    agg = DataAggregator()
    return await agg._fetch_crypto()


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
        return {
            "source": "live",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }
    except Exception as e:
        logger.warning("Live %s fetch failed, falling back to mock: %s", label, e)
        return {
            "source": "mock (fallback)",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": mock_fn(),
        }


@router.get("/snapshot")
async def market_snapshot(
    source: DataSourceEnum = Query(DataSourceEnum.live, description="Data source"),
) -> dict[str, Any]:
    """Quick snapshot: SPX, VIX, DXY, BTC, Gold, Yield Curve."""
    return await _fetch_with_fallback(source, _live_snapshot, get_mock_snapshot, "snapshot")


@router.get("/equities")
async def market_equities(
    source: DataSourceEnum = Query(DataSourceEnum.live, description="Data source"),
) -> dict[str, Any]:
    """US indices, global indices, sectors, VIX."""
    return await _fetch_with_fallback(source, _live_equities, get_mock_equities, "equities")


@router.get("/fx")
async def market_fx(
    source: DataSourceEnum = Query(DataSourceEnum.live, description="Data source"),
) -> dict[str, Any]:
    """FX pairs, DXY, USD strength."""
    return await _fetch_with_fallback(source, _live_fx, get_mock_fx, "fx")


@router.get("/commodities")
async def market_commodities(
    source: DataSourceEnum = Query(DataSourceEnum.live, description="Data source"),
) -> dict[str, Any]:
    """Precious metals, energy, agriculture."""
    return await _fetch_with_fallback(source, _live_commodities, get_mock_commodities, "commodities")


@router.get("/crypto")
async def market_crypto(
    source: DataSourceEnum = Query(DataSourceEnum.live, description="Data source"),
) -> dict[str, Any]:
    """Crypto assets, market overview, fear/greed."""
    return await _fetch_with_fallback(source, _live_crypto, get_mock_crypto, "crypto")
