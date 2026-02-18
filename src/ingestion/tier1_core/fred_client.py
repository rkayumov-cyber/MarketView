"""FRED (Federal Reserve Economic Data) API client."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from fredapi import Fred

from src.config.constants import FRED_SERIES
from src.config.settings import settings
from src.ingestion.base import DataSource


class FREDData:
    """Container for FRED data."""

    def __init__(
        self,
        series_id: str,
        name: str,
        data: pd.DataFrame,
        units: str = "",
        frequency: str = "",
        last_updated: datetime | None = None,
    ) -> None:
        self.series_id = series_id
        self.name = name
        self.data = data
        self.units = units
        self.frequency = frequency
        self.last_updated = last_updated or datetime.utcnow()

    @property
    def latest_value(self) -> float | None:
        """Get most recent value."""
        if self.data.empty:
            return None
        return float(self.data.iloc[-1])

    @property
    def previous_value(self) -> float | None:
        """Get previous value."""
        if len(self.data) < 2:
            return None
        return float(self.data.iloc[-2])

    @property
    def change(self) -> float | None:
        """Get change from previous value."""
        latest = self.latest_value
        previous = self.previous_value
        if latest is None or previous is None:
            return None
        return latest - previous

    @property
    def pct_change(self) -> float | None:
        """Get percentage change from previous value."""
        latest = self.latest_value
        previous = self.previous_value
        if latest is None or previous is None or previous == 0:
            return None
        return ((latest - previous) / previous) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "name": self.name,
            "latest_value": self.latest_value,
            "previous_value": self.previous_value,
            "change": self.change,
            "pct_change": self.pct_change,
            "units": self.units,
            "frequency": self.frequency,
            "last_updated": self.last_updated.isoformat(),
            "data": self.data.reset_index().to_dict(orient="records"),
        }


class FREDClient(DataSource[dict[str, FREDData]]):
    """FRED API client with caching and rate limiting."""

    source_name = "fred"
    cache_ttl = settings.cache_ttl_fred
    rate_limit = settings.rate_limit_fred

    def __init__(self) -> None:
        super().__init__()
        api_key = settings.fred_api_key
        if api_key:
            self._client = Fred(api_key=api_key.get_secret_value())
        else:
            self._client = None
            self.logger.warning("FRED API key not configured")

    async def health_check(self) -> bool:
        """Check FRED API availability."""
        if not self._client:
            return False
        try:
            # Try to fetch a simple series
            await asyncio.to_thread(
                self._client.get_series, "DGS10", limit=1
            )
            return True
        except Exception as e:
            self.logger.error(f"FRED health check failed: {e}")
            return False

    async def fetch_latest(self) -> dict[str, FREDData] | None:
        """Fetch latest data for all configured series."""
        return await self.fetch_multiple(list(FRED_SERIES.keys()))

    async def fetch_series(
        self,
        series_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> FREDData | None:
        """Fetch a single FRED series.

        Args:
            series_name: Friendly name (e.g., 'cpi', 'fed_funds')
            start_date: Start date for data
            end_date: End date for data

        Returns:
            FREDData object or None if error
        """
        if not self._client:
            self.logger.error("FRED client not initialized")
            return None

        series_id = FRED_SERIES.get(series_name)
        if not series_id:
            self.logger.error(f"Unknown series name: {series_name}")
            return None

        # Default to last 2 years of data
        if start_date is None:
            start_date = datetime.now() - timedelta(days=730)
        if end_date is None:
            end_date = datetime.now()

        async def _fetch() -> FREDData | None:
            try:
                data = await asyncio.to_thread(
                    self._client.get_series,
                    series_id,
                    observation_start=start_date,
                    observation_end=end_date,
                )

                info = await asyncio.to_thread(
                    self._client.get_series_info, series_id
                )

                return FREDData(
                    series_id=series_id,
                    name=info.get("title", series_name),
                    data=data,
                    units=info.get("units", ""),
                    frequency=info.get("frequency", ""),
                    last_updated=datetime.utcnow(),
                )
            except Exception as e:
                self.logger.error(f"Error fetching {series_name}: {e}")
                return None

        return await self._with_cache(
            "fetch_series",
            _fetch,
            series_name,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
        )

    async def fetch_multiple(
        self, series_names: list[str]
    ) -> dict[str, FREDData]:
        """Fetch multiple series concurrently."""
        tasks = [self.fetch_series(name) for name in series_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for name, result in zip(series_names, results):
            if isinstance(result, FREDData):
                data[name] = result
            elif isinstance(result, Exception):
                self.logger.error(f"Error fetching {name}: {result}")

        return data

    async def get_inflation_data(self) -> dict[str, FREDData]:
        """Get inflation-related series."""
        series = ["cpi", "core_cpi", "pce", "core_pce", "breakeven_5y", "breakeven_10y"]
        return await self.fetch_multiple(series)

    async def get_rates_data(self) -> dict[str, FREDData]:
        """Get interest rate series."""
        series = ["fed_funds", "treasury_2y", "treasury_10y", "treasury_30y"]
        return await self.fetch_multiple(series)

    async def get_labor_data(self) -> dict[str, FREDData]:
        """Get labor market series."""
        series = ["unemployment", "nonfarm_payrolls", "initial_claims", "continuing_claims"]
        return await self.fetch_multiple(series)

    async def get_growth_data(self) -> dict[str, FREDData]:
        """Get economic growth series."""
        series = ["gdp", "real_gdp", "gdp_growth"]
        return await self.fetch_multiple(series)

    async def get_credit_data(self) -> dict[str, FREDData]:
        """Get credit spread series."""
        series = ["hy_spread", "ig_spread"]
        return await self.fetch_multiple(series)

    async def get_yield_curve(self) -> dict[str, float | None]:
        """Get current yield curve points."""
        rates = await self.get_rates_data()

        curve = {}
        for name, data in rates.items():
            curve[name] = data.latest_value if data else None

        # Calculate 2s10s spread
        t2y = curve.get("treasury_2y")
        t10y = curve.get("treasury_10y")
        if t2y is not None and t10y is not None:
            curve["spread_2s10s"] = t10y - t2y

        return curve
