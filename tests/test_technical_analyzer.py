"""Tests for technical analyzer."""

import pytest

from src.analysis.technical_analyzer import TechnicalAnalyzer


class TestTechnicalAnalyzer:
    """Tests for TechnicalAnalyzer class."""

    def test_analyze_returns_analysis(self, sample_price_data):
        """Test that analyze returns TechnicalAnalysis."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("TEST", sample_price_data)

        assert result is not None
        assert result.symbol == "TEST"
        assert result.current_price > 0

    def test_analyze_support_resistance(self, sample_price_data):
        """Test support/resistance calculation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("TEST", sample_price_data)

        sr = result.support_resistance
        assert sr.support_1 < sr.pivot < sr.resistance_1
        assert sr.support_2 < sr.support_1
        assert sr.resistance_2 > sr.resistance_1

    def test_analyze_momentum(self, sample_price_data):
        """Test momentum indicator calculation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("TEST", sample_price_data)

        momentum = result.momentum
        assert 0 <= momentum.rsi <= 100
        assert momentum.rsi_signal in ["overbought", "oversold", "neutral"]
        assert 0 <= momentum.stochastic_k <= 100

    def test_analyze_trend(self, sample_price_data):
        """Test trend indicator calculation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("TEST", sample_price_data)

        trend = result.trend
        assert trend.macd_trend in ["bullish", "bearish", "neutral"]
        assert trend.sma_20 > 0
        assert trend.sma_50 > 0
        assert trend.sma_200 > 0

    def test_analyze_volatility(self, sample_price_data):
        """Test volatility indicator calculation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("TEST", sample_price_data)

        vol = result.volatility
        assert vol.bb_lower < vol.bb_middle < vol.bb_upper
        assert vol.bb_position in ["upper", "middle", "lower"]
        assert vol.atr > 0

    def test_analyze_overall_signal(self, sample_price_data):
        """Test overall signal generation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("TEST", sample_price_data)

        assert result.overall_signal in ["bullish", "bearish", "neutral"]
        assert 0 <= result.signal_strength <= 1
        assert isinstance(result.signals, list)

    def test_analyze_insufficient_data(self):
        """Test with insufficient data."""
        import pandas as pd

        analyzer = TechnicalAnalyzer()
        df = pd.DataFrame({
            "Open": [100, 101],
            "High": [102, 103],
            "Low": [99, 100],
            "Close": [101, 102],
        })

        result = analyzer.analyze("TEST", df)
        assert result is None

    def test_get_key_levels(self, sample_price_data):
        """Test key levels extraction."""
        analyzer = TechnicalAnalyzer()
        levels = analyzer.get_key_levels("TEST", sample_price_data)

        assert "current_price" in levels
        assert "support_1" in levels
        assert "resistance_1" in levels
        assert "rsi" in levels
        assert "signal" in levels

    def test_to_dict(self, sample_price_data):
        """Test serialization to dict."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze("TEST", sample_price_data)

        data = result.to_dict()

        assert "symbol" in data
        assert "current_price" in data
        assert "support_resistance" in data
        assert "momentum" in data
        assert "trend" in data
        assert "volatility" in data
        assert "overall_signal" in data
