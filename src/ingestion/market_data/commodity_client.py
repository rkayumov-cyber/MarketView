"""Commodity market data client."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import yfinance as yf

from src.config.constants import COMMODITIES
from src.config.settings import settings
from src.ingestion.base import DataSource


@dataclass
class CommodityData:
    """Commodity market data."""

    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    day_high: float
    day_low: float
    volume: int
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "change_percent": self.change_percent,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "volume": self.volume,
            "fifty_two_week_high": self.fifty_two_week_high,
            "fifty_two_week_low": self.fifty_two_week_low,
            "timestamp": self.timestamp.isoformat(),
        }


class CommodityClient(DataSource[dict[str, CommodityData]]):
    """Commodity market data client using Yahoo Finance."""

    source_name = "commodity"
    cache_ttl = settings.cache_ttl_equity
    rate_limit = settings.rate_limit_yahoo

    async def health_check(self) -> bool:
        """Check Yahoo Finance commodity availability."""
        try:
            ticker = yf.Ticker("GC=F")
            await asyncio.to_thread(lambda: ticker.info)
            return True
        except Exception as e:
            self.logger.error(f"Commodity health check failed: {e}")
            return False

    async def fetch_latest(self) -> dict[str, CommodityData] | None:
        """Fetch latest data for all configured commodities."""
        return await self.get_all_commodities()

    async def get_commodity(self, commodity_name: str) -> CommodityData | None:
        """Get data for a specific commodity."""
        symbol = COMMODITIES.get(commodity_name)
        if not symbol:
            self.logger.error(f"Unknown commodity: {commodity_name}")
            return None

        async def _fetch() -> CommodityData | None:
            try:
                ticker = yf.Ticker(symbol)
                info = await asyncio.to_thread(lambda: ticker.info)

                price = info.get("regularMarketPrice", info.get("ask", 0))
                prev_close = info.get("previousClose", info.get("regularMarketPreviousClose", price))

                change = price - prev_close
                change_percent = (change / prev_close * 100) if prev_close else 0

                return CommodityData(
                    symbol=commodity_name,
                    name=info.get("shortName", info.get("longName", commodity_name)),
                    price=price,
                    change=change,
                    change_percent=change_percent,
                    day_high=info.get("regularMarketDayHigh", info.get("dayHigh", 0)),
                    day_low=info.get("regularMarketDayLow", info.get("dayLow", 0)),
                    volume=info.get("regularMarketVolume", info.get("volume", 0)),
                    fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
                    fifty_two_week_low=info.get("fiftyTwoWeekLow"),
                )
            except Exception as e:
                self.logger.error(f"Error fetching {commodity_name}: {e}")
                return None

        return await self._with_cache("get_commodity", _fetch, commodity_name)

    async def get_all_commodities(self) -> dict[str, CommodityData]:
        """Get data for all configured commodities."""
        tasks = [self.get_commodity(name) for name in COMMODITIES.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(COMMODITIES.keys(), results):
            if isinstance(result, CommodityData):
                data[name] = result
            elif isinstance(result, Exception):
                self.logger.error(f"Error fetching {name}: {result}")

        return data

    async def get_precious_metals(self) -> dict[str, CommodityData]:
        """Get precious metals data."""
        metals = ["gold", "silver"]
        tasks = [self.get_commodity(m) for m in metals]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(metals, results):
            if isinstance(result, CommodityData):
                data[name] = result

        return data

    async def get_energy(self) -> dict[str, CommodityData]:
        """Get energy commodities data."""
        energy = ["wti_crude", "brent_crude", "natural_gas"]
        tasks = [self.get_commodity(e) for e in energy]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(energy, results):
            if isinstance(result, CommodityData):
                data[name] = result

        return data

    async def get_agriculture(self) -> dict[str, CommodityData]:
        """Get agricultural commodities data."""
        agriculture = ["corn", "wheat", "soybeans"]
        tasks = [self.get_commodity(a) for a in agriculture]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(agriculture, results):
            if isinstance(result, CommodityData):
                data[name] = result

        return data

    async def get_historical(
        self,
        commodity_name: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> pd.DataFrame | None:
        """Get historical commodity data."""
        symbol = COMMODITIES.get(commodity_name)
        if not symbol:
            return None

        async def _fetch() -> pd.DataFrame | None:
            try:
                ticker = yf.Ticker(symbol)
                history = await asyncio.to_thread(
                    ticker.history,
                    period=period,
                    interval=interval,
                )
                return history
            except Exception as e:
                self.logger.error(f"Error fetching history for {commodity_name}: {e}")
                return None

        return await self._with_cache(
            "get_historical",
            _fetch,
            commodity_name,
            period=period,
            interval=interval,
        )

    async def get_commodity_summary(self) -> dict[str, Any]:
        """Get comprehensive commodity summary."""
        all_commodities = await self.get_all_commodities()

        # Group by category
        precious = {k: v for k, v in all_commodities.items() if k in ["gold", "silver"]}
        energy = {k: v for k, v in all_commodities.items() if k in ["wti_crude", "brent_crude", "natural_gas"]}
        agriculture = {k: v for k, v in all_commodities.items() if k in ["corn", "wheat", "soybeans"]}
        industrial = {k: v for k, v in all_commodities.items() if k in ["copper"]}

        return {
            "precious_metals": {k: v.to_dict() for k, v in precious.items()},
            "energy": {k: v.to_dict() for k, v in energy.items()},
            "agriculture": {k: v.to_dict() for k, v in agriculture.items()},
            "industrial": {k: v.to_dict() for k, v in industrial.items()},
            "timestamp": datetime.now(UTC).isoformat(),
        }
