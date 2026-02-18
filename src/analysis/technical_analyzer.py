"""Technical analysis engine for market data."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange

from src.config.constants import TECHNICAL


@dataclass
class SupportResistance:
    """Support and resistance levels."""

    support_1: float
    support_2: float
    resistance_1: float
    resistance_2: float
    pivot: float

    def to_dict(self) -> dict[str, float]:
        return {
            "support_1": self.support_1,
            "support_2": self.support_2,
            "resistance_1": self.resistance_1,
            "resistance_2": self.resistance_2,
            "pivot": self.pivot,
        }


@dataclass
class MomentumIndicators:
    """Momentum indicator values."""

    rsi: float
    rsi_signal: str  # "overbought", "oversold", "neutral"
    stochastic_k: float
    stochastic_d: float
    stochastic_signal: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rsi": self.rsi,
            "rsi_signal": self.rsi_signal,
            "stochastic_k": self.stochastic_k,
            "stochastic_d": self.stochastic_d,
            "stochastic_signal": self.stochastic_signal,
        }


@dataclass
class TrendIndicators:
    """Trend indicator values."""

    macd: float
    macd_signal: float
    macd_histogram: float
    macd_trend: str  # "bullish", "bearish", "neutral"
    sma_20: float
    sma_50: float
    sma_200: float
    price_vs_sma: dict[str, str]  # "above" or "below" for each SMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "macd_trend": self.macd_trend,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "sma_200": self.sma_200,
            "price_vs_sma": self.price_vs_sma,
        }


@dataclass
class VolatilityIndicators:
    """Volatility indicator values."""

    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_width: float
    bb_position: str  # "upper", "middle", "lower"
    atr: float
    atr_percent: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "bb_upper": self.bb_upper,
            "bb_middle": self.bb_middle,
            "bb_lower": self.bb_lower,
            "bb_width": self.bb_width,
            "bb_position": self.bb_position,
            "atr": self.atr,
            "atr_percent": self.atr_percent,
        }


@dataclass
class TechnicalAnalysis:
    """Complete technical analysis result."""

    symbol: str
    current_price: float
    support_resistance: SupportResistance
    momentum: MomentumIndicators
    trend: TrendIndicators
    volatility: VolatilityIndicators
    overall_signal: str  # "bullish", "bearish", "neutral"
    signal_strength: float  # 0-1
    signals: list[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "support_resistance": self.support_resistance.to_dict(),
            "momentum": self.momentum.to_dict(),
            "trend": self.trend.to_dict(),
            "volatility": self.volatility.to_dict(),
            "overall_signal": self.overall_signal,
            "signal_strength": self.signal_strength,
            "signals": self.signals,
            "timestamp": self.timestamp.isoformat(),
        }


class TechnicalAnalyzer:
    """Technical analysis engine."""

    def __init__(self) -> None:
        self.rsi_period = TECHNICAL["rsi_period"]
        self.rsi_overbought = TECHNICAL["rsi_overbought"]
        self.rsi_oversold = TECHNICAL["rsi_oversold"]
        self.macd_fast = TECHNICAL["macd_fast"]
        self.macd_slow = TECHNICAL["macd_slow"]
        self.macd_signal = TECHNICAL["macd_signal"]
        self.bb_period = TECHNICAL["bb_period"]
        self.bb_std = TECHNICAL["bb_std"]

    def analyze(self, symbol: str, data: pd.DataFrame) -> TechnicalAnalysis | None:
        """Perform complete technical analysis on price data.

        Args:
            symbol: Asset symbol
            data: DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)

        Returns:
            TechnicalAnalysis result or None if insufficient data
        """
        if data is None or len(data) < 200:
            return None

        # Ensure we have the required columns
        required = ["Open", "High", "Low", "Close"]
        if not all(col in data.columns for col in required):
            return None

        current_price = float(data["Close"].iloc[-1])

        # Calculate all indicators
        sr = self._calculate_support_resistance(data)
        momentum = self._calculate_momentum(data)
        trend = self._calculate_trend(data, current_price)
        volatility = self._calculate_volatility(data, current_price)

        # Generate overall signal
        signal, strength, signals = self._generate_signal(
            momentum, trend, volatility, sr, current_price
        )

        return TechnicalAnalysis(
            symbol=symbol,
            current_price=current_price,
            support_resistance=sr,
            momentum=momentum,
            trend=trend,
            volatility=volatility,
            overall_signal=signal,
            signal_strength=strength,
            signals=signals,
        )

    def _calculate_support_resistance(self, data: pd.DataFrame) -> SupportResistance:
        """Calculate support and resistance levels using pivot points."""
        high = float(data["High"].iloc[-1])
        low = float(data["Low"].iloc[-1])
        close = float(data["Close"].iloc[-1])

        # Standard pivot point formula
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)

        return SupportResistance(
            support_1=round(s1, 2),
            support_2=round(s2, 2),
            resistance_1=round(r1, 2),
            resistance_2=round(r2, 2),
            pivot=round(pivot, 2),
        )

    def _calculate_momentum(self, data: pd.DataFrame) -> MomentumIndicators:
        """Calculate momentum indicators."""
        close = data["Close"]
        high = data["High"]
        low = data["Low"]

        # RSI
        rsi_indicator = RSIIndicator(close, window=self.rsi_period)
        rsi = float(rsi_indicator.rsi().iloc[-1])

        if rsi >= self.rsi_overbought:
            rsi_signal = "overbought"
        elif rsi <= self.rsi_oversold:
            rsi_signal = "oversold"
        else:
            rsi_signal = "neutral"

        # Stochastic
        stoch = StochasticOscillator(high, low, close)
        stoch_k = float(stoch.stoch().iloc[-1])
        stoch_d = float(stoch.stoch_signal().iloc[-1])

        if stoch_k > 80:
            stoch_signal = "overbought"
        elif stoch_k < 20:
            stoch_signal = "oversold"
        else:
            stoch_signal = "neutral"

        return MomentumIndicators(
            rsi=round(rsi, 2),
            rsi_signal=rsi_signal,
            stochastic_k=round(stoch_k, 2),
            stochastic_d=round(stoch_d, 2),
            stochastic_signal=stoch_signal,
        )

    def _calculate_trend(self, data: pd.DataFrame, current_price: float) -> TrendIndicators:
        """Calculate trend indicators."""
        close = data["Close"]

        # MACD
        macd_indicator = MACD(
            close,
            window_slow=self.macd_slow,
            window_fast=self.macd_fast,
            window_sign=self.macd_signal,
        )
        macd = float(macd_indicator.macd().iloc[-1])
        macd_sig = float(macd_indicator.macd_signal().iloc[-1])
        macd_hist = float(macd_indicator.macd_diff().iloc[-1])

        if macd > macd_sig and macd_hist > 0:
            macd_trend = "bullish"
        elif macd < macd_sig and macd_hist < 0:
            macd_trend = "bearish"
        else:
            macd_trend = "neutral"

        # SMAs
        sma_20 = float(SMAIndicator(close, window=20).sma_indicator().iloc[-1])
        sma_50 = float(SMAIndicator(close, window=50).sma_indicator().iloc[-1])
        sma_200 = float(SMAIndicator(close, window=200).sma_indicator().iloc[-1])

        price_vs_sma = {
            "sma_20": "above" if current_price > sma_20 else "below",
            "sma_50": "above" if current_price > sma_50 else "below",
            "sma_200": "above" if current_price > sma_200 else "below",
        }

        return TrendIndicators(
            macd=round(macd, 4),
            macd_signal=round(macd_sig, 4),
            macd_histogram=round(macd_hist, 4),
            macd_trend=macd_trend,
            sma_20=round(sma_20, 2),
            sma_50=round(sma_50, 2),
            sma_200=round(sma_200, 2),
            price_vs_sma=price_vs_sma,
        )

    def _calculate_volatility(
        self, data: pd.DataFrame, current_price: float
    ) -> VolatilityIndicators:
        """Calculate volatility indicators."""
        close = data["Close"]
        high = data["High"]
        low = data["Low"]

        # Bollinger Bands
        bb = BollingerBands(close, window=self.bb_period, window_dev=self.bb_std)
        bb_upper = float(bb.bollinger_hband().iloc[-1])
        bb_middle = float(bb.bollinger_mavg().iloc[-1])
        bb_lower = float(bb.bollinger_lband().iloc[-1])
        bb_width = (bb_upper - bb_lower) / bb_middle * 100

        # Determine BB position
        if current_price > bb_upper:
            bb_position = "upper"
        elif current_price < bb_lower:
            bb_position = "lower"
        else:
            bb_position = "middle"

        # ATR
        atr_indicator = AverageTrueRange(high, low, close)
        atr = float(atr_indicator.average_true_range().iloc[-1])
        atr_percent = (atr / current_price) * 100

        return VolatilityIndicators(
            bb_upper=round(bb_upper, 2),
            bb_middle=round(bb_middle, 2),
            bb_lower=round(bb_lower, 2),
            bb_width=round(bb_width, 2),
            bb_position=bb_position,
            atr=round(atr, 2),
            atr_percent=round(atr_percent, 2),
        )

    def _generate_signal(
        self,
        momentum: MomentumIndicators,
        trend: TrendIndicators,
        volatility: VolatilityIndicators,
        sr: SupportResistance,
        current_price: float,
    ) -> tuple[str, float, list[str]]:
        """Generate overall trading signal."""
        signals = []
        bullish_score = 0
        bearish_score = 0

        # Momentum signals
        if momentum.rsi_signal == "oversold":
            signals.append("RSI oversold - potential bounce")
            bullish_score += 1
        elif momentum.rsi_signal == "overbought":
            signals.append("RSI overbought - potential pullback")
            bearish_score += 1

        if momentum.stochastic_signal == "oversold":
            bullish_score += 0.5
        elif momentum.stochastic_signal == "overbought":
            bearish_score += 0.5

        # Trend signals
        if trend.macd_trend == "bullish":
            signals.append("MACD bullish crossover")
            bullish_score += 1
        elif trend.macd_trend == "bearish":
            signals.append("MACD bearish crossover")
            bearish_score += 1

        # SMA signals
        above_count = sum(1 for v in trend.price_vs_sma.values() if v == "above")
        if above_count == 3:
            signals.append("Price above all major SMAs - strong uptrend")
            bullish_score += 1.5
        elif above_count == 0:
            signals.append("Price below all major SMAs - strong downtrend")
            bearish_score += 1.5
        elif trend.price_vs_sma["sma_200"] == "above":
            signals.append("Price above 200 SMA - long-term uptrend")
            bullish_score += 0.5

        # Volatility signals
        if volatility.bb_position == "lower":
            signals.append("Price at lower Bollinger Band - oversold")
            bullish_score += 0.5
        elif volatility.bb_position == "upper":
            signals.append("Price at upper Bollinger Band - overbought")
            bearish_score += 0.5

        # Support/Resistance proximity
        distance_to_support = (current_price - sr.support_1) / current_price * 100
        distance_to_resistance = (sr.resistance_1 - current_price) / current_price * 100

        if distance_to_support < 1:
            signals.append(f"Near support at {sr.support_1}")
        if distance_to_resistance < 1:
            signals.append(f"Near resistance at {sr.resistance_1}")

        # Calculate overall signal
        total_score = bullish_score + bearish_score
        if total_score == 0:
            return "neutral", 0.5, signals

        net_score = bullish_score - bearish_score
        strength = abs(net_score) / total_score

        if net_score > 0.5:
            signal = "bullish"
        elif net_score < -0.5:
            signal = "bearish"
        else:
            signal = "neutral"

        return signal, round(strength, 2), signals

    def get_key_levels(
        self, symbol: str, data: pd.DataFrame
    ) -> dict[str, Any]:
        """Get key technical levels for quick reference."""
        analysis = self.analyze(symbol, data)
        if not analysis:
            return {}

        return {
            "symbol": symbol,
            "current_price": analysis.current_price,
            "pivot": analysis.support_resistance.pivot,
            "support_1": analysis.support_resistance.support_1,
            "support_2": analysis.support_resistance.support_2,
            "resistance_1": analysis.support_resistance.resistance_1,
            "resistance_2": analysis.support_resistance.resistance_2,
            "sma_20": analysis.trend.sma_20,
            "sma_50": analysis.trend.sma_50,
            "sma_200": analysis.trend.sma_200,
            "rsi": analysis.momentum.rsi,
            "signal": analysis.overall_signal,
        }
