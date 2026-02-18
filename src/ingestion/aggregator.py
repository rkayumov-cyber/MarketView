"""Aggregated data service combining all data sources."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.ingestion.tier1_core import FREDClient
from src.ingestion.tier2_sentiment import RedditClient
from src.ingestion.market_data import CryptoClient, EquityClient, FXClient
from src.ingestion.market_data.commodity_client import CommodityClient

logger = logging.getLogger(__name__)


@dataclass
class MarketSnapshot:
    """Complete market snapshot aggregating all data sources."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    macro: dict[str, Any] = field(default_factory=dict)
    equities: dict[str, Any] = field(default_factory=dict)
    fixed_income: dict[str, Any] = field(default_factory=dict)
    fx: dict[str, Any] = field(default_factory=dict)
    commodities: dict[str, Any] = field(default_factory=dict)
    crypto: dict[str, Any] = field(default_factory=dict)
    sentiment: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "macro": self.macro,
            "equities": self.equities,
            "fixed_income": self.fixed_income,
            "fx": self.fx,
            "commodities": self.commodities,
            "crypto": self.crypto,
            "sentiment": self.sentiment,
            "errors": self.errors,
        }


class DataAggregator:
    """Aggregates data from all sources into unified snapshots."""

    def __init__(self) -> None:
        self.fred = FREDClient()
        self.reddit = RedditClient()
        self.crypto = CryptoClient()
        self.equity = EquityClient()
        self.fx = FXClient()
        self.commodity = CommodityClient()
        self.logger = logging.getLogger(__name__)

    async def get_full_snapshot(self) -> MarketSnapshot:
        """Get complete market snapshot from all sources."""
        snapshot = MarketSnapshot()

        # Run all fetches concurrently
        tasks = {
            "macro": self._fetch_macro(),
            "equities": self._fetch_equities(),
            "fixed_income": self._fetch_fixed_income(),
            "fx": self._fetch_fx(),
            "commodities": self._fetch_commodities(),
            "crypto": self._fetch_crypto(),
            "sentiment": self._fetch_sentiment(),
        }

        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True,
        )

        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                error_msg = f"{key}: {str(result)}"
                self.logger.error(f"Error fetching {key}: {result}")
                snapshot.errors.append(error_msg)
            else:
                setattr(snapshot, key, result)

        return snapshot

    async def _fetch_macro(self) -> dict[str, Any]:
        """Fetch macroeconomic data."""
        inflation = await self.fred.get_inflation_data()
        growth = await self.fred.get_growth_data()
        labor = await self.fred.get_labor_data()

        return {
            "inflation": {k: v.to_dict() for k, v in inflation.items()},
            "growth": {k: v.to_dict() for k, v in growth.items()},
            "labor": {k: v.to_dict() for k, v in labor.items()},
        }

    async def _fetch_equities(self) -> dict[str, Any]:
        """Fetch equity market data."""
        us_indices = await self.equity.get_us_indices()
        global_indices = await self.equity.get_global_indices()
        sectors = await self.equity.get_sector_performance()
        vix = await self.equity.get_vix()

        return {
            "us": {k: v.to_dict() for k, v in us_indices.items()},
            "global": {k: v.to_dict() for k, v in global_indices.items()},
            "sectors": sectors,
            "vix": vix.to_dict() if vix else None,
        }

    async def _fetch_fixed_income(self) -> dict[str, Any]:
        """Fetch fixed income data."""
        rates = await self.fred.get_rates_data()
        yield_curve = await self.fred.get_yield_curve()
        credit = await self.fred.get_credit_data()

        return {
            "rates": {k: v.to_dict() for k, v in rates.items()},
            "yield_curve": yield_curve,
            "credit": {k: v.to_dict() for k, v in credit.items()},
        }

    async def _fetch_fx(self) -> dict[str, Any]:
        """Fetch FX data."""
        return await self.fx.get_fx_summary()

    async def _fetch_commodities(self) -> dict[str, Any]:
        """Fetch commodity data."""
        return await self.commodity.get_commodity_summary()

    async def _fetch_crypto(self) -> dict[str, Any]:
        """Fetch cryptocurrency data."""
        crypto_data = await self.crypto.fetch_latest()
        market_overview = await self.crypto.get_market_overview()
        fear_greed = await self.crypto.get_fear_greed_proxy()

        return {
            "assets": {k: v.to_dict() for k, v in (crypto_data or {}).items()},
            "market_overview": market_overview.to_dict() if market_overview else None,
            "fear_greed": fear_greed,
        }

    async def _fetch_sentiment(self) -> dict[str, Any]:
        """Fetch sentiment data."""
        return await self.reddit.get_overall_sentiment()

    async def get_quick_snapshot(self) -> dict[str, Any]:
        """Get a quick snapshot with key metrics only."""
        # Fetch only the most essential data
        tasks = {
            "spx": self.equity.get_quote("^GSPC"),
            "vix": self.equity.get_vix(),
            "dxy": self.fx.get_dxy(),
            "bitcoin": self.crypto.get_crypto_data(["bitcoin"]),
            "gold": self.commodity.get_commodity("gold"),
            "yield_curve": self.fred.get_yield_curve(),
        }

        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True,
        )

        snapshot = {"timestamp": datetime.now(UTC).isoformat()}

        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                self.logger.error(f"Error fetching {key}: {result}")
                snapshot[key] = None
            elif hasattr(result, "to_dict"):
                snapshot[key] = result.to_dict()
            elif isinstance(result, dict):
                if "bitcoin" in result:
                    snapshot[key] = result["bitcoin"].to_dict()
                else:
                    snapshot[key] = result
            else:
                snapshot[key] = result

        return snapshot

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all data sources."""
        checks = {
            "fred": self.fred.health_check(),
            "reddit": self.reddit.health_check(),
            "crypto": self.crypto.health_check(),
            "equity": self.equity.health_check(),
            "fx": self.fx.health_check(),
            "commodity": self.commodity.health_check(),
        }

        results = await asyncio.gather(*checks.values(), return_exceptions=True)

        health = {}
        for name, result in zip(checks.keys(), results):
            if isinstance(result, Exception):
                health[name] = False
            else:
                health[name] = result

        return health
