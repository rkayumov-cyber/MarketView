"""Market regime detection and classification."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.config.constants import MarketRegime
from src.ingestion.aggregator import DataAggregator


@dataclass
class RegimeIndicators:
    """Indicators used for regime detection."""

    cpi_yoy: float | None = None
    core_pce_yoy: float | None = None
    gdp_growth: float | None = None
    unemployment: float | None = None
    fed_funds: float | None = None
    yield_curve_2s10s: float | None = None
    vix: float | None = None
    credit_spread_hy: float | None = None
    spx_change_pct: float | None = None


@dataclass
class MarketRegimeResult:
    """Market regime classification result."""

    regime: MarketRegime
    confidence: float  # 0-1
    description: str
    indicators: RegimeIndicators
    signals: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime.value,
            "confidence": self.confidence,
            "description": self.description,
            "indicators": {
                "cpi_yoy": self.indicators.cpi_yoy,
                "core_pce_yoy": self.indicators.core_pce_yoy,
                "gdp_growth": self.indicators.gdp_growth,
                "unemployment": self.indicators.unemployment,
                "fed_funds": self.indicators.fed_funds,
                "yield_curve_2s10s": self.indicators.yield_curve_2s10s,
                "vix": self.indicators.vix,
                "credit_spread_hy": self.indicators.credit_spread_hy,
                "spx_change_pct": self.indicators.spx_change_pct,
            },
            "signals": self.signals,
            "timestamp": self.timestamp.isoformat(),
        }


class RegimeDetector:
    """Detects and classifies market regimes."""

    # Regime thresholds
    INFLATION_HIGH = 3.0  # CPI YoY threshold
    INFLATION_LOW = 1.5
    GROWTH_HIGH = 2.5  # GDP growth threshold
    GROWTH_LOW = 1.0
    VIX_HIGH = 25
    VIX_EXTREME = 35
    CREDIT_SPREAD_TIGHT = 3.0
    CREDIT_SPREAD_WIDE = 5.0

    def __init__(self) -> None:
        self.aggregator = DataAggregator()

    async def detect_regime(self) -> MarketRegimeResult:
        """Detect current market regime."""
        # Fetch required data
        snapshot = await self.aggregator.get_full_snapshot()

        # Extract indicators
        indicators = self._extract_indicators(snapshot)

        # Classify regime
        regime, confidence, description, signals = self._classify_regime(indicators)

        return MarketRegimeResult(
            regime=regime,
            confidence=confidence,
            description=description,
            indicators=indicators,
            signals=signals,
        )

    def _extract_indicators(self, snapshot: dict[str, Any]) -> RegimeIndicators:
        """Extract regime indicators from snapshot."""
        indicators = RegimeIndicators()

        # Macro indicators
        macro = snapshot.macro if hasattr(snapshot, "macro") else snapshot.get("macro", {})
        inflation = macro.get("inflation", {})
        growth = macro.get("growth", {})
        labor = macro.get("labor", {})

        if "cpi" in inflation:
            indicators.cpi_yoy = inflation["cpi"].get("pct_change")
        if "core_pce" in inflation:
            indicators.core_pce_yoy = inflation["core_pce"].get("pct_change")
        if "gdp_growth" in growth:
            indicators.gdp_growth = growth["gdp_growth"].get("latest_value")
        if "unemployment" in labor:
            indicators.unemployment = labor["unemployment"].get("latest_value")

        # Fixed income
        fixed_income = snapshot.fixed_income if hasattr(snapshot, "fixed_income") else snapshot.get("fixed_income", {})
        rates = fixed_income.get("rates", {})
        yield_curve = fixed_income.get("yield_curve", {})
        credit = fixed_income.get("credit", {})

        if "fed_funds" in rates:
            indicators.fed_funds = rates["fed_funds"].get("latest_value")
        if "spread_2s10s" in yield_curve:
            indicators.yield_curve_2s10s = yield_curve["spread_2s10s"]
        if "hy_spread" in credit:
            indicators.credit_spread_hy = credit["hy_spread"].get("latest_value")

        # Equities
        equities = snapshot.equities if hasattr(snapshot, "equities") else snapshot.get("equities", {})
        if equities.get("vix"):
            indicators.vix = equities["vix"].get("current_price")
        us = equities.get("us", {})
        if "spx" in us:
            indicators.spx_change_pct = us["spx"].get("change_percent")

        return indicators

    def _classify_regime(
        self, indicators: RegimeIndicators
    ) -> tuple[MarketRegime, float, str, list[str]]:
        """Classify market regime based on indicators."""
        signals: list[str] = []
        scores: dict[MarketRegime, float] = {regime: 0.0 for regime in MarketRegime}

        # Inflation assessment
        inflation = indicators.cpi_yoy or indicators.core_pce_yoy
        if inflation is not None:
            if inflation > self.INFLATION_HIGH:
                signals.append(f"High inflation ({inflation:.1f}%)")
                scores[MarketRegime.INFLATIONARY_EXPANSION] += 0.3
                scores[MarketRegime.STAGFLATION] += 0.3
            elif inflation < self.INFLATION_LOW:
                signals.append(f"Low inflation ({inflation:.1f}%)")
                scores[MarketRegime.DEFLATIONARY] += 0.3
                scores[MarketRegime.GOLDILOCKS] += 0.2
            else:
                signals.append(f"Moderate inflation ({inflation:.1f}%)")
                scores[MarketRegime.GOLDILOCKS] += 0.3

        # Growth assessment
        growth = indicators.gdp_growth
        if growth is not None:
            if growth > self.GROWTH_HIGH:
                signals.append(f"Strong growth ({growth:.1f}%)")
                scores[MarketRegime.INFLATIONARY_EXPANSION] += 0.3
                scores[MarketRegime.GOLDILOCKS] += 0.2
            elif growth < self.GROWTH_LOW:
                signals.append(f"Weak growth ({growth:.1f}%)")
                scores[MarketRegime.STAGFLATION] += 0.3
                scores[MarketRegime.DEFLATIONARY] += 0.3
            else:
                signals.append(f"Moderate growth ({growth:.1f}%)")
                scores[MarketRegime.GOLDILOCKS] += 0.3

        # VIX assessment (risk sentiment)
        vix = indicators.vix
        if vix is not None:
            if vix > self.VIX_EXTREME:
                signals.append(f"Extreme volatility (VIX: {vix:.1f})")
                scores[MarketRegime.RISK_OFF] += 0.4
            elif vix > self.VIX_HIGH:
                signals.append(f"Elevated volatility (VIX: {vix:.1f})")
                scores[MarketRegime.RISK_OFF] += 0.2
            elif vix < 15:
                signals.append(f"Low volatility (VIX: {vix:.1f})")
                scores[MarketRegime.RISK_ON] += 0.3
                scores[MarketRegime.GOLDILOCKS] += 0.2

        # Yield curve assessment
        curve = indicators.yield_curve_2s10s
        if curve is not None:
            if curve < 0:
                signals.append(f"Inverted yield curve ({curve:.2f}%)")
                scores[MarketRegime.STAGFLATION] += 0.2
                scores[MarketRegime.DEFLATIONARY] += 0.2
            elif curve > 1.5:
                signals.append(f"Steep yield curve ({curve:.2f}%)")
                scores[MarketRegime.INFLATIONARY_EXPANSION] += 0.2

        # Credit spread assessment
        credit = indicators.credit_spread_hy
        if credit is not None:
            if credit > self.CREDIT_SPREAD_WIDE:
                signals.append(f"Wide credit spreads ({credit:.0f}bps)")
                scores[MarketRegime.RISK_OFF] += 0.3
            elif credit < self.CREDIT_SPREAD_TIGHT:
                signals.append(f"Tight credit spreads ({credit:.0f}bps)")
                scores[MarketRegime.RISK_ON] += 0.3

        # Find regime with highest score
        best_regime = max(scores, key=scores.get)
        best_score = scores[best_regime]

        # Calculate confidence based on score strength
        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.5

        # Generate description
        description = self._generate_description(best_regime, indicators, signals)

        return best_regime, confidence, description, signals

    def _generate_description(
        self,
        regime: MarketRegime,
        indicators: RegimeIndicators,
        signals: list[str],
    ) -> str:
        """Generate narrative description of current regime."""
        descriptions = {
            MarketRegime.GOLDILOCKS: (
                "Markets are in a Goldilocks environment with moderate growth, "
                "contained inflation, and supportive financial conditions. "
                "Risk assets typically perform well in this regime."
            ),
            MarketRegime.INFLATIONARY_EXPANSION: (
                "Economy is experiencing inflationary expansion with strong growth "
                "accompanied by rising prices. Central banks may tighten policy. "
                "Commodities and value stocks tend to outperform."
            ),
            MarketRegime.STAGFLATION: (
                "Stagflationary conditions are emerging with weak growth coupled "
                "with elevated inflation. This challenging environment typically "
                "favors defensive positioning and real assets."
            ),
            MarketRegime.DEFLATIONARY: (
                "Deflationary pressures are building with weak growth and falling "
                "prices. Central banks may ease policy. Duration and quality "
                "typically outperform in this environment."
            ),
            MarketRegime.RISK_OFF: (
                "Markets are in risk-off mode with elevated volatility and "
                "widening credit spreads. Investors are seeking safe havens. "
                "Defensive assets and hedges are favored."
            ),
            MarketRegime.RISK_ON: (
                "Risk appetite is elevated with low volatility and tight spreads. "
                "Investors are positioned for upside. Higher beta and credit "
                "assets tend to outperform."
            ),
        }

        return descriptions.get(regime, "Market regime unclear.")

    async def get_regime_history(self, days: int = 30) -> list[dict[str, Any]]:
        """Get regime classifications over time."""
        # This would typically pull from a database
        # For now, return current regime only
        current = await self.detect_regime()
        return [current.to_dict()]

    def get_regime_implications(self, regime: MarketRegime) -> dict[str, Any]:
        """Get asset class implications for a given regime."""
        implications = {
            MarketRegime.GOLDILOCKS: {
                "equities": {"bias": "bullish", "sectors": ["tech", "growth"]},
                "fixed_income": {"bias": "neutral", "duration": "moderate"},
                "fx": {"bias": "neutral", "carry": "favorable"},
                "commodities": {"bias": "neutral"},
                "crypto": {"bias": "bullish"},
            },
            MarketRegime.INFLATIONARY_EXPANSION: {
                "equities": {"bias": "cautious", "sectors": ["energy", "materials", "financials"]},
                "fixed_income": {"bias": "bearish", "duration": "short"},
                "fx": {"bias": "usd_bullish"},
                "commodities": {"bias": "bullish"},
                "crypto": {"bias": "mixed"},
            },
            MarketRegime.STAGFLATION: {
                "equities": {"bias": "bearish", "sectors": ["staples", "utilities", "healthcare"]},
                "fixed_income": {"bias": "cautious", "tips": "favorable"},
                "fx": {"bias": "safe_haven"},
                "commodities": {"bias": "bullish", "focus": ["gold"]},
                "crypto": {"bias": "bearish"},
            },
            MarketRegime.DEFLATIONARY: {
                "equities": {"bias": "bearish", "sectors": ["tech", "staples"]},
                "fixed_income": {"bias": "bullish", "duration": "long"},
                "fx": {"bias": "usd_bullish"},
                "commodities": {"bias": "bearish"},
                "crypto": {"bias": "mixed"},
            },
            MarketRegime.RISK_OFF: {
                "equities": {"bias": "bearish", "sectors": ["staples", "utilities"]},
                "fixed_income": {"bias": "bullish", "quality": "high"},
                "fx": {"bias": "safe_haven"},
                "commodities": {"bias": "mixed", "focus": ["gold"]},
                "crypto": {"bias": "bearish"},
            },
            MarketRegime.RISK_ON: {
                "equities": {"bias": "bullish", "sectors": ["tech", "discretionary"]},
                "fixed_income": {"bias": "neutral", "credit": "favorable"},
                "fx": {"bias": "risk_currencies"},
                "commodities": {"bias": "neutral"},
                "crypto": {"bias": "bullish"},
            },
        }

        return implications.get(regime, {})
