"""CoinGecko cryptocurrency data client."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pycoingecko import CoinGeckoAPI

from src.config.constants import CRYPTO_IDS
from src.config.settings import settings
from src.ingestion.base import DataSource


@dataclass
class CryptoData:
    """Cryptocurrency market data."""

    id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    market_cap_rank: int
    total_volume: float
    high_24h: float
    low_24h: float
    price_change_24h: float
    price_change_percentage_24h: float
    price_change_percentage_7d: float | None = None
    price_change_percentage_30d: float | None = None
    circulating_supply: float | None = None
    total_supply: float | None = None
    ath: float | None = None
    ath_change_percentage: float | None = None
    atl: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "current_price": self.current_price,
            "market_cap": self.market_cap,
            "market_cap_rank": self.market_cap_rank,
            "total_volume": self.total_volume,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "price_change_24h": self.price_change_24h,
            "price_change_percentage_24h": self.price_change_percentage_24h,
            "price_change_percentage_7d": self.price_change_percentage_7d,
            "price_change_percentage_30d": self.price_change_percentage_30d,
            "circulating_supply": self.circulating_supply,
            "total_supply": self.total_supply,
            "ath": self.ath,
            "ath_change_percentage": self.ath_change_percentage,
            "atl": self.atl,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CryptoMarketOverview:
    """Overall crypto market data."""

    total_market_cap: float
    total_volume: float
    btc_dominance: float
    eth_dominance: float
    market_cap_change_24h: float
    active_cryptocurrencies: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_market_cap": self.total_market_cap,
            "total_volume": self.total_volume,
            "btc_dominance": self.btc_dominance,
            "eth_dominance": self.eth_dominance,
            "market_cap_change_24h": self.market_cap_change_24h,
            "active_cryptocurrencies": self.active_cryptocurrencies,
            "timestamp": self.timestamp.isoformat(),
        }


class CryptoClient(DataSource[dict[str, CryptoData]]):
    """CoinGecko API client for cryptocurrency data."""

    source_name = "crypto"
    cache_ttl = settings.cache_ttl_crypto
    rate_limit = settings.rate_limit_coingecko

    def __init__(self) -> None:
        super().__init__()
        self._client = CoinGeckoAPI()

    async def health_check(self) -> bool:
        """Check CoinGecko API availability."""
        try:
            await asyncio.to_thread(self._client.ping)
            return True
        except Exception as e:
            self.logger.error(f"CoinGecko health check failed: {e}")
            return False

    async def fetch_latest(self) -> dict[str, CryptoData] | None:
        """Fetch latest data for all configured cryptocurrencies."""
        return await self.get_crypto_data(list(CRYPTO_IDS.values()))

    async def get_crypto_data(
        self,
        coin_ids: list[str],
        vs_currency: str = "usd",
    ) -> dict[str, CryptoData]:
        """Fetch data for specific cryptocurrencies."""

        async def _fetch() -> dict[str, CryptoData]:
            try:
                data = await asyncio.to_thread(
                    self._client.get_coins_markets,
                    vs_currency=vs_currency,
                    ids=",".join(coin_ids),
                    order="market_cap_desc",
                    per_page=len(coin_ids),
                    price_change_percentage="24h,7d,30d",
                )

                result = {}
                for coin in data:
                    result[coin["id"]] = CryptoData(
                        id=coin["id"],
                        symbol=coin["symbol"].upper(),
                        name=coin["name"],
                        current_price=coin["current_price"],
                        market_cap=coin["market_cap"],
                        market_cap_rank=coin["market_cap_rank"],
                        total_volume=coin["total_volume"],
                        high_24h=coin["high_24h"],
                        low_24h=coin["low_24h"],
                        price_change_24h=coin["price_change_24h"],
                        price_change_percentage_24h=coin["price_change_percentage_24h"],
                        price_change_percentage_7d=coin.get("price_change_percentage_7d_in_currency"),
                        price_change_percentage_30d=coin.get("price_change_percentage_30d_in_currency"),
                        circulating_supply=coin.get("circulating_supply"),
                        total_supply=coin.get("total_supply"),
                        ath=coin.get("ath"),
                        ath_change_percentage=coin.get("ath_change_percentage"),
                        atl=coin.get("atl"),
                    )
                return result
            except Exception as e:
                self.logger.error(f"Error fetching crypto data: {e}")
                return {}

        return await self._with_cache(
            "get_crypto_data",
            _fetch,
            ",".join(sorted(coin_ids)),
            vs_currency=vs_currency,
        )

    async def get_market_overview(self) -> CryptoMarketOverview | None:
        """Get overall crypto market statistics."""

        async def _fetch() -> CryptoMarketOverview | None:
            try:
                data = await asyncio.to_thread(self._client.get_global)

                market_data = data["data"]
                return CryptoMarketOverview(
                    total_market_cap=market_data["total_market_cap"]["usd"],
                    total_volume=market_data["total_volume"]["usd"],
                    btc_dominance=market_data["market_cap_percentage"]["btc"],
                    eth_dominance=market_data["market_cap_percentage"]["eth"],
                    market_cap_change_24h=market_data["market_cap_change_percentage_24h_usd"],
                    active_cryptocurrencies=market_data["active_cryptocurrencies"],
                )
            except Exception as e:
                self.logger.error(f"Error fetching market overview: {e}")
                return None

        return await self._with_cache("get_market_overview", _fetch)

    async def get_historical_prices(
        self,
        coin_id: str,
        days: int = 30,
        vs_currency: str = "usd",
    ) -> list[tuple[datetime, float]] | None:
        """Get historical price data for a coin."""

        async def _fetch() -> list[tuple[datetime, float]] | None:
            try:
                data = await asyncio.to_thread(
                    self._client.get_coin_market_chart_by_id,
                    id=coin_id,
                    vs_currency=vs_currency,
                    days=days,
                )

                prices = []
                for timestamp, price in data["prices"]:
                    dt = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
                    prices.append((dt, price))

                return prices
            except Exception as e:
                self.logger.error(f"Error fetching historical prices for {coin_id}: {e}")
                return None

        return await self._with_cache(
            "get_historical_prices",
            _fetch,
            coin_id,
            days=days,
            vs_currency=vs_currency,
        )

    async def get_fear_greed_proxy(self) -> dict[str, Any]:
        """Estimate fear/greed using price volatility and dominance."""
        overview = await self.get_market_overview()
        btc_data = await self.get_crypto_data(["bitcoin"])

        if not overview or "bitcoin" not in btc_data:
            return {"error": "Unable to calculate fear/greed proxy"}

        btc = btc_data["bitcoin"]

        # Simple fear/greed proxy based on:
        # - 24h price change
        # - Distance from ATH
        # - BTC dominance (higher = more fear)

        # Normalize 24h change to 0-100
        change_score = min(100, max(0, (btc.price_change_percentage_24h + 10) * 5))

        # ATH distance score
        ath_score = 100 + btc.ath_change_percentage if btc.ath_change_percentage else 50

        # Dominance score (inverse - lower dominance = more greed)
        dominance_score = 100 - overview.btc_dominance

        # Weighted average
        fear_greed = (change_score * 0.4 + ath_score * 0.3 + dominance_score * 0.3)
        fear_greed = min(100, max(0, fear_greed))

        if fear_greed >= 75:
            classification = "Extreme Greed"
        elif fear_greed >= 55:
            classification = "Greed"
        elif fear_greed >= 45:
            classification = "Neutral"
        elif fear_greed >= 25:
            classification = "Fear"
        else:
            classification = "Extreme Fear"

        return {
            "value": round(fear_greed, 1),
            "classification": classification,
            "components": {
                "price_momentum": round(change_score, 1),
                "ath_distance": round(ath_score, 1),
                "dominance": round(dominance_score, 1),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
