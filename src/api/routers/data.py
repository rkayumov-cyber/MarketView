"""Data API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.config.constants import FRED_SERIES
from src.ingestion.tier1_core import FREDClient

router = APIRouter()


@router.get("/fred/series/{series_name}")
async def get_fred_series(
    series_name: str,
    start_date: datetime | None = Query(None, description="Start date for data"),
    end_date: datetime | None = Query(None, description="End date for data"),
) -> dict[str, Any]:
    """Get a specific FRED series."""
    if series_name not in FRED_SERIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown series. Available: {list(FRED_SERIES.keys())}",
        )

    client = FREDClient()
    data = await client.fetch_series(series_name, start_date, end_date)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch FRED data")

    return data.to_dict()


@router.get("/fred/series")
async def list_fred_series() -> dict[str, Any]:
    """List available FRED series."""
    return {
        "series": FRED_SERIES,
        "count": len(FRED_SERIES),
    }


@router.get("/fred/inflation")
async def get_inflation_data() -> dict[str, Any]:
    """Get inflation-related data."""
    client = FREDClient()
    data = await client.get_inflation_data()

    return {
        "category": "inflation",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {k: v.to_dict() for k, v in data.items()},
    }


@router.get("/fred/rates")
async def get_rates_data() -> dict[str, Any]:
    """Get interest rate data."""
    client = FREDClient()
    data = await client.get_rates_data()

    return {
        "category": "rates",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {k: v.to_dict() for k, v in data.items()},
    }


@router.get("/fred/labor")
async def get_labor_data() -> dict[str, Any]:
    """Get labor market data."""
    client = FREDClient()
    data = await client.get_labor_data()

    return {
        "category": "labor",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {k: v.to_dict() for k, v in data.items()},
    }


@router.get("/fred/growth")
async def get_growth_data() -> dict[str, Any]:
    """Get economic growth data."""
    client = FREDClient()
    data = await client.get_growth_data()

    return {
        "category": "growth",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {k: v.to_dict() for k, v in data.items()},
    }


@router.get("/fred/credit")
async def get_credit_data() -> dict[str, Any]:
    """Get credit spread data."""
    client = FREDClient()
    data = await client.get_credit_data()

    return {
        "category": "credit",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {k: v.to_dict() for k, v in data.items()},
    }


@router.get("/fred/yield-curve")
async def get_yield_curve() -> dict[str, Any]:
    """Get current yield curve."""
    client = FREDClient()
    curve = await client.get_yield_curve()

    return {
        "category": "yield_curve",
        "timestamp": datetime.utcnow().isoformat(),
        "data": curve,
    }
