"""Cross-asset correlation analysis engine."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from src.ingestion.market_data import EquityClient, FXClient, CryptoClient
from src.ingestion.market_data.commodity_client import CommodityClient


@dataclass
class CorrelationPair:
    """Correlation between two assets."""

    asset1: str
    asset2: str
    correlation: float
    period_days: int
    strength: str  # "strong_positive", "moderate_positive", "weak", "moderate_negative", "strong_negative"

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset1": self.asset1,
            "asset2": self.asset2,
            "correlation": self.correlation,
            "period_days": self.period_days,
            "strength": self.strength,
        }


@dataclass
class CorrelationMatrix:
    """Full correlation matrix."""

    assets: list[str]
    matrix: list[list[float]]
    period_days: int
    notable_pairs: list[CorrelationPair]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "assets": self.assets,
            "matrix": self.matrix,
            "period_days": self.period_days,
            "notable_pairs": [p.to_dict() for p in self.notable_pairs],
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RollingCorrelation:
    """Rolling correlation over time."""

    asset1: str
    asset2: str
    window: int
    correlations: list[tuple[datetime, float]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset1": self.asset1,
            "asset2": self.asset2,
            "window": self.window,
            "correlations": [
                {"date": d.isoformat(), "correlation": c}
                for d, c in self.correlations
            ],
        }


class CorrelationEngine:
    """Cross-asset correlation analysis."""

    # Standard asset universe for correlation
    CORE_ASSETS = {
        "SPX": "^GSPC",
        "NDX": "^IXIC",
        "VIX": "^VIX",
        "DXY": "DX-Y.NYB",
        "Gold": "GC=F",
        "WTI": "CL=F",
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "US10Y": "^TNX",
        "EURUSD": "EURUSD=X",
    }

    def __init__(self) -> None:
        self.equity = EquityClient()
        self.fx = FXClient()
        self.crypto = CryptoClient()
        self.commodity = CommodityClient()

    async def build_correlation_matrix(
        self,
        assets: list[str] | None = None,
        period_days: int = 90,
    ) -> CorrelationMatrix:
        """Build correlation matrix for specified assets."""
        if assets is None:
            assets = list(self.CORE_ASSETS.keys())

        # Fetch historical data for all assets
        price_data = await self._fetch_price_data(assets, period_days)

        # Calculate correlation matrix
        df = pd.DataFrame(price_data)

        # Calculate returns
        returns = df.pct_change().dropna()

        # Compute correlation matrix
        corr_matrix = returns.corr()

        # Convert to list format
        matrix_list = corr_matrix.values.tolist()
        matrix_list = [[round(x, 3) if not np.isnan(x) else 0 for x in row] for row in matrix_list]

        # Find notable pairs
        notable = self._find_notable_correlations(corr_matrix, period_days)

        return CorrelationMatrix(
            assets=list(corr_matrix.columns),
            matrix=matrix_list,
            period_days=period_days,
            notable_pairs=notable,
        )

    async def _fetch_price_data(
        self,
        assets: list[str],
        period_days: int,
    ) -> dict[str, pd.Series]:
        """Fetch historical price data for assets."""
        price_data = {}
        period = f"{period_days}d"

        for asset in assets:
            symbol = self.CORE_ASSETS.get(asset, asset)

            try:
                if asset in ["BTC", "ETH"]:
                    # Crypto - use CoinGecko
                    crypto_id = "bitcoin" if asset == "BTC" else "ethereum"
                    prices = await self.crypto.get_historical_prices(
                        crypto_id, days=period_days
                    )
                    if prices:
                        price_data[asset] = pd.Series(
                            {d: p for d, p in prices},
                            name=asset,
                        )
                else:
                    # Use yfinance for everything else
                    import yfinance as yf
                    ticker = yf.Ticker(symbol)
                    hist = await asyncio.to_thread(
                        ticker.history, period=period
                    )
                    if not hist.empty:
                        price_data[asset] = hist["Close"]
                        price_data[asset].name = asset

            except Exception as e:
                print(f"Error fetching {asset}: {e}")
                continue

        return price_data

    def _find_notable_correlations(
        self,
        corr_matrix: pd.DataFrame,
        period_days: int,
    ) -> list[CorrelationPair]:
        """Find notably strong or weak correlations."""
        notable = []
        n = len(corr_matrix)

        for i in range(n):
            for j in range(i + 1, n):
                corr = corr_matrix.iloc[i, j]

                if np.isnan(corr):
                    continue

                # Determine strength
                if corr >= 0.7:
                    strength = "strong_positive"
                    is_notable = True
                elif corr >= 0.4:
                    strength = "moderate_positive"
                    is_notable = corr >= 0.5
                elif corr <= -0.7:
                    strength = "strong_negative"
                    is_notable = True
                elif corr <= -0.4:
                    strength = "moderate_negative"
                    is_notable = corr <= -0.5
                else:
                    strength = "weak"
                    is_notable = False

                if is_notable:
                    notable.append(CorrelationPair(
                        asset1=corr_matrix.columns[i],
                        asset2=corr_matrix.columns[j],
                        correlation=round(float(corr), 3),
                        period_days=period_days,
                        strength=strength,
                    ))

        # Sort by absolute correlation
        notable.sort(key=lambda x: abs(x.correlation), reverse=True)

        return notable[:10]  # Return top 10 notable pairs

    async def get_rolling_correlation(
        self,
        asset1: str,
        asset2: str,
        window: int = 30,
        period_days: int = 365,
    ) -> RollingCorrelation | None:
        """Calculate rolling correlation between two assets."""
        price_data = await self._fetch_price_data([asset1, asset2], period_days)

        if asset1 not in price_data or asset2 not in price_data:
            return None

        # Create DataFrame and align
        df = pd.DataFrame({
            asset1: price_data[asset1],
            asset2: price_data[asset2],
        })
        df = df.dropna()

        if len(df) < window:
            return None

        # Calculate returns
        returns = df.pct_change().dropna()

        # Calculate rolling correlation
        rolling_corr = returns[asset1].rolling(window).corr(returns[asset2])
        rolling_corr = rolling_corr.dropna()

        correlations = [
            (idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx, float(val))
            for idx, val in rolling_corr.items()
        ]

        return RollingCorrelation(
            asset1=asset1,
            asset2=asset2,
            window=window,
            correlations=correlations,
        )

    async def get_regime_correlations(self) -> dict[str, Any]:
        """Get correlations relevant for regime assessment."""
        # Key pairs for regime detection
        regime_pairs = [
            ("SPX", "VIX"),  # Risk sentiment
            ("SPX", "Gold"),  # Risk-off indicator
            ("Gold", "DXY"),  # Dollar vs safe haven
            ("BTC", "SPX"),  # Crypto-equity correlation
            ("SPX", "US10Y"),  # Equity-bond correlation
            ("WTI", "DXY"),  # Oil-dollar inverse
        ]

        results = {}
        for asset1, asset2 in regime_pairs:
            try:
                matrix = await self.build_correlation_matrix(
                    [asset1, asset2], period_days=30
                )
                if matrix.matrix and len(matrix.matrix) > 1:
                    corr = matrix.matrix[0][1]
                    results[f"{asset1}/{asset2}"] = {
                        "correlation_30d": corr,
                        "interpretation": self._interpret_correlation(asset1, asset2, corr),
                    }
            except Exception as e:
                results[f"{asset1}/{asset2}"] = {"error": str(e)}

        return results

    def _interpret_correlation(self, asset1: str, asset2: str, corr: float) -> str:
        """Interpret correlation for specific asset pairs."""
        pair = f"{asset1}/{asset2}"

        interpretations = {
            "SPX/VIX": {
                "high_neg": "Normal risk-off behavior - VIX spiking on equity weakness",
                "low_neg": "Complacent markets - VIX not responding to moves",
                "positive": "Unusual - VIX rising with equities, check for hedging activity",
            },
            "SPX/Gold": {
                "high_neg": "Strong risk-off bid for gold",
                "low_neg": "Gold trading independently",
                "positive": "Risk-on/liquidity-driven, both benefiting from easy money",
            },
            "BTC/SPX": {
                "high_pos": "Crypto trading as risk asset - correlated with equities",
                "low": "Crypto decoupling from traditional markets",
                "high_neg": "Unusual - crypto as hedge (rare)",
            },
        }

        pair_interp = interpretations.get(pair, {})

        if corr <= -0.6:
            return pair_interp.get("high_neg", "Strong negative correlation")
        elif corr <= -0.3:
            return pair_interp.get("low_neg", "Moderate negative correlation")
        elif corr >= 0.6:
            return pair_interp.get("high_pos", "Strong positive correlation")
        elif corr >= 0.3:
            return pair_interp.get("positive", "Moderate positive correlation")
        else:
            return pair_interp.get("low", "Weak correlation - assets trading independently")

    async def get_tail_risk_indicators(self) -> dict[str, Any]:
        """Get correlation-based tail risk indicators."""
        # Tail risk is often indicated by correlation breakdown
        # or convergence to 1 (all assets move together)

        matrix = await self.build_correlation_matrix(period_days=30)

        # Calculate average cross-correlation
        n = len(matrix.matrix)
        total_corr = 0
        count = 0

        for i in range(n):
            for j in range(i + 1, n):
                total_corr += abs(matrix.matrix[i][j])
                count += 1

        avg_corr = total_corr / count if count > 0 else 0

        # Check for correlation convergence (all moving together = crisis)
        if avg_corr > 0.7:
            risk_level = "elevated"
            assessment = (
                "High cross-asset correlation indicates risk-off/crisis mode. "
                "Diversification benefits reduced."
            )
        elif avg_corr > 0.5:
            risk_level = "moderate"
            assessment = (
                "Moderately elevated correlations. Markets somewhat synchronized."
            )
        else:
            risk_level = "normal"
            assessment = (
                "Normal correlation environment. Diversification benefits intact."
            )

        return {
            "average_cross_correlation": round(avg_corr, 3),
            "risk_level": risk_level,
            "assessment": assessment,
            "notable_pairs": [p.to_dict() for p in matrix.notable_pairs[:5]],
        }
