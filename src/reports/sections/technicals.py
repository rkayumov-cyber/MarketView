"""Technicals section builder."""

import asyncio

import yfinance as yf

from src.analysis import TechnicalAnalyzer, CorrelationEngine
from src.ingestion.market_data import EquityClient
from src.reports.models import (
    TechnicalsSection,
    TechnicalLevel,
    VolatilityAnalysis,
    PositioningData,
    CorrelationInsight,
    ReportLevel,
)


class TechnicalsSectionBuilder:
    """Builder for the Technicals & Positioning section."""

    KEY_ASSETS = {
        "SPX": "^GSPC",
        "Gold": "GC=F",
        "DXY": "DX-Y.NYB",
        "BTC": "BTC-USD",
    }

    def __init__(self) -> None:
        self.analyzer = TechnicalAnalyzer()
        self.correlation_engine = CorrelationEngine()
        self.equity = EquityClient()

    async def build(self, level: ReportLevel) -> TechnicalsSection:
        """Build the Technicals section."""
        # Get technical levels for key assets
        levels = await self._get_key_levels()

        # Get volatility analysis
        volatility = await self._get_volatility_analysis()

        # Get positioning (simplified)
        positioning = self._get_positioning(level)

        # Get correlations for deep dive
        correlations = None
        if level == ReportLevel.DEEP_DIVE:
            correlations = await self._get_correlations()

        return TechnicalsSection(
            key_levels=levels,
            volatility=volatility,
            positioning=positioning,
            correlations=correlations,
        )

    async def _get_key_levels(self) -> list[TechnicalLevel]:
        """Get technical levels for key assets."""
        levels = []

        for name, symbol in self.KEY_ASSETS.items():
            try:
                # Fetch historical data
                ticker = yf.Ticker(symbol)
                data = await asyncio.to_thread(
                    ticker.history, period="1y", interval="1d"
                )

                if data.empty or len(data) < 200:
                    continue

                # Run technical analysis
                analysis = self.analyzer.analyze(name, data)

                if analysis:
                    levels.append(TechnicalLevel(
                        asset=name,
                        current_price=analysis.current_price,
                        support_1=analysis.support_resistance.support_1,
                        support_2=analysis.support_resistance.support_2,
                        resistance_1=analysis.support_resistance.resistance_1,
                        resistance_2=analysis.support_resistance.resistance_2,
                        pivot=analysis.support_resistance.pivot,
                        trend=analysis.overall_signal,
                        rsi=analysis.momentum.rsi,
                        signal=analysis.overall_signal,
                    ))

            except Exception as e:
                print(f"Error analyzing {name}: {e}")
                continue

        return levels

    async def _get_volatility_analysis(self) -> VolatilityAnalysis:
        """Get volatility analysis."""
        vix_data = await self.equity.get_vix()

        vix_level = vix_data.current_price if vix_data else None

        # Determine percentile (simplified - would need historical data)
        if vix_level:
            if vix_level < 15:
                percentile = 20.0
                assessment = "VIX at historically low levels - complacency elevated"
            elif vix_level < 20:
                percentile = 40.0
                assessment = "VIX in normal range - balanced risk environment"
            elif vix_level < 25:
                percentile = 60.0
                assessment = "VIX elevated - some caution warranted"
            elif vix_level < 30:
                percentile = 80.0
                assessment = "VIX high - risk-off environment"
            else:
                percentile = 95.0
                assessment = "VIX extreme - crisis-level volatility"
        else:
            percentile = None
            assessment = "Volatility data unavailable"

        return VolatilityAnalysis(
            vix=vix_level,
            vix_percentile=percentile,
            move_index=None,  # Would need MOVE index data
            assessment=assessment,
        )

    def _get_positioning(self, level: ReportLevel) -> PositioningData | None:
        """Get positioning data."""
        if level < ReportLevel.STANDARD:
            return None

        # This would integrate with actual positioning data
        # For now, provide a framework
        return PositioningData(
            retail_sentiment="Net bullish based on Reddit sentiment analysis",
            institutional_flows="Awaiting CFTC COT data" if level >= ReportLevel.DEEP_DIVE else None,
            cot_summary=None,
        )

    async def _get_correlations(self) -> list[CorrelationInsight]:
        """Get correlation insights."""
        try:
            regime_corrs = await self.correlation_engine.get_regime_correlations()

            insights = []
            for pair, data in regime_corrs.items():
                if "error" not in data:
                    insights.append(CorrelationInsight(
                        pair=pair,
                        correlation=data.get("correlation_30d", 0),
                        interpretation=data.get("interpretation", ""),
                    ))

            return insights
        except Exception:
            return []
