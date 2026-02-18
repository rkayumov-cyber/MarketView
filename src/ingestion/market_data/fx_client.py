"""Foreign exchange market data client."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd
import yfinance as yf

from src.config.constants import FX_PAIRS
from src.config.settings import settings
from src.ingestion.base import DataSource


@dataclass
class FXData:
    """FX pair market data."""

    pair: str
    rate: float
    change: float
    change_percent: float
    day_high: float
    day_low: float
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair": self.pair,
            "rate": self.rate,
            "change": self.change,
            "change_percent": self.change_percent,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "fifty_two_week_high": self.fifty_two_week_high,
            "fifty_two_week_low": self.fifty_two_week_low,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DXYData:
    """Dollar Index data."""

    value: float
    change: float
    change_percent: float
    day_high: float
    day_low: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "change": self.change,
            "change_percent": self.change_percent,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "timestamp": self.timestamp.isoformat(),
        }


class FXClient(DataSource[dict[str, FXData]]):
    """FX market data client using Yahoo Finance."""

    source_name = "fx"
    cache_ttl = settings.cache_ttl_equity
    rate_limit = settings.rate_limit_yahoo

    async def health_check(self) -> bool:
        """Check Yahoo Finance FX availability."""
        try:
            ticker = yf.Ticker("EURUSD=X")
            await asyncio.to_thread(lambda: ticker.info)
            return True
        except Exception as e:
            self.logger.error(f"FX health check failed: {e}")
            return False

    async def fetch_latest(self) -> dict[str, FXData] | None:
        """Fetch latest data for all configured FX pairs."""
        return await self.get_all_pairs()

    async def get_pair(self, pair_name: str) -> FXData | None:
        """Get data for a specific FX pair."""
        symbol = FX_PAIRS.get(pair_name)
        if not symbol:
            self.logger.error(f"Unknown FX pair: {pair_name}")
            return None

        async def _fetch() -> FXData | None:
            try:
                ticker = yf.Ticker(symbol)
                info = await asyncio.to_thread(lambda: ticker.info)

                rate = info.get("regularMarketPrice", info.get("ask", 0))
                prev_close = info.get("previousClose", info.get("regularMarketPreviousClose", rate))

                change = rate - prev_close
                change_percent = (change / prev_close * 100) if prev_close else 0

                return FXData(
                    pair=pair_name.upper(),
                    rate=rate,
                    change=change,
                    change_percent=change_percent,
                    day_high=info.get("regularMarketDayHigh", info.get("dayHigh", 0)),
                    day_low=info.get("regularMarketDayLow", info.get("dayLow", 0)),
                    fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
                    fifty_two_week_low=info.get("fiftyTwoWeekLow"),
                )
            except Exception as e:
                self.logger.error(f"Error fetching {pair_name}: {e}")
                return None

        return await self._with_cache("get_pair", _fetch, pair_name)

    async def get_all_pairs(self) -> dict[str, FXData]:
        """Get data for all configured FX pairs."""
        tasks = [self.get_pair(name) for name in FX_PAIRS.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(FX_PAIRS.keys(), results):
            if isinstance(result, FXData):
                data[name] = result
            elif isinstance(result, Exception):
                self.logger.error(f"Error fetching {name}: {result}")

        return data

    async def get_dxy(self) -> DXYData | None:
        """Get Dollar Index (DXY) data."""

        async def _fetch() -> DXYData | None:
            try:
                ticker = yf.Ticker("DX-Y.NYB")
                info = await asyncio.to_thread(lambda: ticker.info)

                value = info.get("regularMarketPrice", info.get("ask", 0))
                prev_close = info.get("previousClose", info.get("regularMarketPreviousClose", value))

                change = value - prev_close
                change_percent = (change / prev_close * 100) if prev_close else 0

                return DXYData(
                    value=value,
                    change=change,
                    change_percent=change_percent,
                    day_high=info.get("regularMarketDayHigh", info.get("dayHigh", 0)),
                    day_low=info.get("regularMarketDayLow", info.get("dayLow", 0)),
                )
            except Exception as e:
                self.logger.error(f"Error fetching DXY: {e}")
                return None

        return await self._with_cache("get_dxy", _fetch)

    async def get_historical(
        self,
        pair_name: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> pd.DataFrame | None:
        """Get historical FX data."""
        symbol = FX_PAIRS.get(pair_name)
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
                self.logger.error(f"Error fetching history for {pair_name}: {e}")
                return None

        return await self._with_cache(
            "get_historical",
            _fetch,
            pair_name,
            period=period,
            interval=interval,
        )

    async def get_dm_pairs(self) -> dict[str, FXData]:
        """Get developed market FX pairs."""
        dm_pairs = ["eurusd", "usdjpy", "gbpusd", "usdchf", "audusd", "usdcad"]
        tasks = [self.get_pair(p) for p in dm_pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(dm_pairs, results):
            if isinstance(result, FXData):
                data[name] = result

        return data

    async def get_em_pairs(self) -> dict[str, FXData]:
        """Get emerging market FX pairs."""
        em_pairs = ["usdcnh", "usdmxn", "usdbrl"]
        tasks = [self.get_pair(p) for p in em_pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(em_pairs, results):
            if isinstance(result, FXData):
                data[name] = result

        return data

    async def get_fx_summary(self) -> dict[str, Any]:
        """Get comprehensive FX market summary."""
        all_pairs = await self.get_all_pairs()
        dxy = await self.get_dxy()

        # Categorize by strength
        usd_strength = []
        for name, data in all_pairs.items():
            # For USD/XXX pairs, positive change = USD strength
            # For XXX/USD pairs, negative change = USD strength
            if name.startswith("usd"):
                usd_strength.append(data.change_percent)
            else:
                usd_strength.append(-data.change_percent)

        avg_usd_strength = sum(usd_strength) / len(usd_strength) if usd_strength else 0

        return {
            "dxy": dxy.to_dict() if dxy else None,
            "pairs": {k: v.to_dict() for k, v in all_pairs.items()},
            "usd_strength_index": avg_usd_strength,
            "timestamp": datetime.utcnow().isoformat(),
        }
