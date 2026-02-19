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
from src.ingestion.market_data import twelve_data_client as td

logger = logging.getLogger(__name__)

router = APIRouter()


class DataSourceEnum(str, Enum):
    live = "live"
    mock = "mock"


def _source_tag(data: dict, td_keys: list[str], yf_keys: list[str]) -> str:
    """Determine source tag based on which keys have data."""
    has_td = any(data.get(k) for k in td_keys)
    has_yf = any(data.get(k) for k in yf_keys)
    if has_td and has_yf:
        return "live (twelvedata+yfinance)"
    if has_td:
        return "live (twelvedata)"
    if has_yf:
        return "live (yfinance)"
    return "live"


async def _live_snapshot() -> tuple[dict[str, Any], str]:
    data = await td.fetch_snapshot()
    tag = _source_tag(data, ["bitcoin", "gold"], ["spx", "vix", "dxy"])
    return data, tag


async def _live_equities() -> tuple[dict[str, Any], str]:
    data = await td.fetch_equities()
    return data, "live (yfinance)"


async def _live_fx() -> tuple[dict[str, Any], str]:
    data = await td.fetch_fx()
    return data, "live (yfinance)"


async def _live_commodities() -> tuple[dict[str, Any], str]:
    data = await td.fetch_commodities()
    return data, "live (yfinance)"


async def _live_crypto() -> tuple[dict[str, Any], str]:
    data = await td.fetch_crypto()
    return data, "live (twelvedata)"


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
        data, source_tag = await live_fn()
        if data:
            return {
                "source": source_tag,
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
