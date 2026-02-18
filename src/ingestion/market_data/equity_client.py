"""Equity market data client using yfinance."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from src.config.constants import INDICES
from src.config.settings import settings
from src.ingestion.base import DataSource


@dataclass
class EquityData:
    """Equity/index market data."""

    symbol: str
    name: str
    current_price: float
    previous_close: float
    open_price: float
    day_high: float
    day_low: float
    volume: int
    change: float
    change_percent: float
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    dividend_yield: float | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "current_price": self.current_price,
            "previous_close": self.previous_close,
            "open_price": self.open_price,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "volume": self.volume,
            "change": self.change,
            "change_percent": self.change_percent,
            "fifty_two_week_high": self.fifty_two_week_high,
            "fifty_two_week_low": self.fifty_two_week_low,
            "market_cap": self.market_cap,
            "pe_ratio": self.pe_ratio,
            "dividend_yield": self.dividend_yield,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MarketBreadth:
    """Market breadth indicators."""

    advancing: int
    declining: int
    unchanged: int
    advance_decline_ratio: float
    new_highs: int
    new_lows: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "advancing": self.advancing,
            "declining": self.declining,
            "unchanged": self.unchanged,
            "advance_decline_ratio": self.advance_decline_ratio,
            "new_highs": self.new_highs,
            "new_lows": self.new_lows,
            "timestamp": self.timestamp.isoformat(),
        }


class EquityClient(DataSource[dict[str, EquityData]]):
    """Yahoo Finance client for equity and index data."""

    source_name = "equity"
    cache_ttl = settings.cache_ttl_equity
    rate_limit = settings.rate_limit_yahoo

    async def health_check(self) -> bool:
        """Check Yahoo Finance availability."""
        try:
            ticker = yf.Ticker("^GSPC")
            await asyncio.to_thread(lambda: ticker.info)
            return True
        except Exception as e:
            self.logger.error(f"Yahoo Finance health check failed: {e}")
            return False

    async def fetch_latest(self) -> dict[str, EquityData] | None:
        """Fetch latest data for all configured indices."""
        return await self.get_indices()

    async def get_quote(self, symbol: str) -> EquityData | None:
        """Get quote for a single symbol."""

        async def _fetch() -> EquityData | None:
            try:
                ticker = yf.Ticker(symbol)
                info = await asyncio.to_thread(lambda: ticker.info)

                # Handle missing data gracefully
                current_price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
                previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose", current_price)

                change = current_price - previous_close
                change_percent = (change / previous_close * 100) if previous_close else 0

                return EquityData(
                    symbol=symbol,
                    name=info.get("shortName", info.get("longName", symbol)),
                    current_price=current_price,
                    previous_close=previous_close,
                    open_price=info.get("regularMarketOpen", info.get("open", 0)),
                    day_high=info.get("regularMarketDayHigh", info.get("dayHigh", 0)),
                    day_low=info.get("regularMarketDayLow", info.get("dayLow", 0)),
                    volume=info.get("regularMarketVolume", info.get("volume", 0)),
                    change=change,
                    change_percent=change_percent,
                    fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
                    fifty_two_week_low=info.get("fiftyTwoWeekLow"),
                    market_cap=info.get("marketCap"),
                    pe_ratio=info.get("trailingPE"),
                    dividend_yield=info.get("dividendYield"),
                )
            except Exception as e:
                self.logger.error(f"Error fetching {symbol}: {e}")
                return None

        return await self._with_cache("get_quote", _fetch, symbol)

    async def get_indices(self) -> dict[str, EquityData]:
        """Get data for all major indices."""
        tasks = [self.get_quote(symbol) for symbol in INDICES.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(INDICES.keys(), results):
            if isinstance(result, EquityData):
                data[name] = result
            elif isinstance(result, Exception):
                self.logger.error(f"Error fetching {name}: {result}")

        return data

    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> pd.DataFrame | None:
        """Get historical price data."""

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
                self.logger.error(f"Error fetching history for {symbol}: {e}")
                return None

        return await self._with_cache(
            "get_historical",
            _fetch,
            symbol,
            period=period,
            interval=interval,
        )

    async def get_vix(self) -> EquityData | None:
        """Get VIX data."""
        return await self.get_quote("^VIX")

    async def get_sector_performance(self) -> dict[str, float]:
        """Get sector ETF performance."""
        sector_etfs = {
            "technology": "XLK",
            "healthcare": "XLV",
            "financials": "XLF",
            "consumer_discretionary": "XLY",
            "consumer_staples": "XLP",
            "industrials": "XLI",
            "energy": "XLE",
            "materials": "XLB",
            "utilities": "XLU",
            "real_estate": "XLRE",
            "communication": "XLC",
        }

        tasks = [self.get_quote(symbol) for symbol in sector_etfs.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        performance = {}
        for sector, result in zip(sector_etfs.keys(), results):
            if isinstance(result, EquityData):
                performance[sector] = result.change_percent

        return performance

    async def get_market_summary(self) -> dict[str, Any]:
        """Get overall market summary."""
        indices = await self.get_indices()
        vix = await self.get_vix()
        sectors = await self.get_sector_performance()

        # Calculate market breadth from index changes
        advancing = sum(1 for d in indices.values() if d.change_percent > 0)
        declining = sum(1 for d in indices.values() if d.change_percent < 0)
        unchanged = len(indices) - advancing - declining

        return {
            "indices": {k: v.to_dict() for k, v in indices.items()},
            "vix": vix.to_dict() if vix else None,
            "sectors": sectors,
            "breadth": {
                "advancing": advancing,
                "declining": declining,
                "unchanged": unchanged,
                "ratio": advancing / declining if declining > 0 else float("inf"),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_us_indices(self) -> dict[str, EquityData]:
        """Get US market indices."""
        us_symbols = ["spx", "nasdaq", "dow", "russell2000"]
        tasks = [self.get_quote(INDICES[s]) for s in us_symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(us_symbols, results):
            if isinstance(result, EquityData):
                data[name] = result

        return data

    async def get_global_indices(self) -> dict[str, EquityData]:
        """Get global market indices."""
        global_symbols = ["nikkei", "eurostoxx50", "ftse100", "dax", "hang_seng", "shanghai", "nifty50"]
        tasks = [self.get_quote(INDICES[s]) for s in global_symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(global_symbols, results):
            if isinstance(result, EquityData):
                data[name] = result

        return data
