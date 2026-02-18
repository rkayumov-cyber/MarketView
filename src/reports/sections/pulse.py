"""Pulse section builder - The current market narrative."""

from src.analysis import RegimeDetector
from src.ingestion.tier2_sentiment import RedditClient
from src.reports.models import (
    PulseSection,
    MarketRegimeInfo,
    SentimentInfo,
    DivergenceInfo,
    ReportLevel,
)


class PulseSectionBuilder:
    """Builder for the Pulse section."""

    def __init__(self) -> None:
        self.regime_detector = RegimeDetector()
        self.reddit = RedditClient()

    async def build(self, level: ReportLevel) -> PulseSection:
        """Build the Pulse section."""
        # Get regime analysis
        regime_result = await self.regime_detector.detect_regime()

        regime = MarketRegimeInfo(
            regime=regime_result.regime.value,
            confidence=regime_result.confidence,
            description=regime_result.description,
            signals=regime_result.signals,
        )

        # Get sentiment if available
        sentiment = None
        if level >= ReportLevel.STANDARD:
            try:
                sentiment_data = await self.reddit.get_overall_sentiment()
                if "error" not in sentiment_data:
                    sentiment = SentimentInfo(
                        overall_score=sentiment_data.get("overall_sentiment", 0),
                        bullish_ratio=sentiment_data.get("overall_bullish_ratio", 0.5),
                        trending_tickers=sentiment_data.get("trending_tickers", []),
                    )
            except Exception:
                pass

        # Check for divergences
        divergences = self._check_divergences(regime_result, sentiment)

        # Generate the big narrative
        big_narrative = self._generate_narrative(regime_result, sentiment, level)

        # Key takeaways
        takeaways = self._generate_takeaways(regime_result, sentiment, level)

        return PulseSection(
            regime=regime,
            sentiment=sentiment,
            divergences=divergences,
            big_narrative=big_narrative,
            key_takeaways=takeaways,
        )

    def _check_divergences(
        self,
        regime_result,
        sentiment: SentimentInfo | None,
    ) -> list[DivergenceInfo]:
        """Check for data vs sentiment divergences."""
        divergences = []

        if not sentiment:
            return divergences

        # Check regime vs sentiment
        regime = regime_result.regime.value

        # Bullish sentiment in risk-off regime
        if regime in ["risk_off", "stagflation"] and sentiment.bullish_ratio > 0.6:
            divergences.append(DivergenceInfo(
                has_divergence=True,
                description="Retail sentiment remains bullish despite risk-off signals",
                data_signal="Risk-off regime indicated by macro data",
                sentiment_signal=f"{sentiment.bullish_ratio:.0%} bullish sentiment",
            ))

        # Bearish sentiment in goldilocks regime
        if regime == "goldilocks" and sentiment.bullish_ratio < 0.4:
            divergences.append(DivergenceInfo(
                has_divergence=True,
                description="Bearish sentiment despite favorable macro conditions",
                data_signal="Goldilocks regime with low inflation and steady growth",
                sentiment_signal=f"Only {sentiment.bullish_ratio:.0%} bullish sentiment",
            ))

        return divergences

    def _generate_narrative(
        self,
        regime_result,
        sentiment: SentimentInfo | None,
        level: ReportLevel,
    ) -> str:
        """Generate the big narrative summary."""
        regime = regime_result.regime.value.replace("_", " ").title()

        # Build narrative based on level
        if level == ReportLevel.EXECUTIVE:
            return (
                f"Markets in {regime} mode. "
                f"Confidence: {regime_result.confidence:.0%}. "
                f"{regime_result.description[:100]}..."
            )

        narrative = f"Markets are currently in a **{regime}** environment "
        narrative += f"(confidence: {regime_result.confidence:.0%}). "
        narrative += regime_result.description

        if sentiment and level >= ReportLevel.STANDARD:
            sentiment_word = "bullish" if sentiment.bullish_ratio > 0.5 else "bearish"
            narrative += (
                f"\n\nRetail sentiment is {sentiment_word} with "
                f"{sentiment.bullish_ratio:.0%} bullish positioning. "
            )

            if sentiment.trending_tickers:
                top_tickers = [t[0] for t in sentiment.trending_tickers[:5]]
                narrative += f"Trending tickers: {', '.join(top_tickers)}."

        return narrative

    def _generate_takeaways(
        self,
        regime_result,
        sentiment: SentimentInfo | None,
        level: ReportLevel,
    ) -> list[str]:
        """Generate key takeaways."""
        takeaways = []

        # Regime-based takeaways
        implications = self.regime_detector.get_regime_implications(regime_result.regime)

        if implications.get("equities", {}).get("bias") == "bullish":
            takeaways.append("Equity bias: Bullish - favor risk assets")
        elif implications.get("equities", {}).get("bias") == "bearish":
            takeaways.append("Equity bias: Bearish - defensive positioning warranted")

        if implications.get("fixed_income", {}).get("duration") == "short":
            takeaways.append("Duration: Keep duration short in rising rate environment")
        elif implications.get("fixed_income", {}).get("duration") == "long":
            takeaways.append("Duration: Extend duration for potential rate cuts")

        # Add signals as takeaways
        for signal in regime_result.signals[:3]:
            takeaways.append(signal)

        # Limit based on level
        max_takeaways = {
            ReportLevel.EXECUTIVE: 3,
            ReportLevel.STANDARD: 5,
            ReportLevel.DEEP_DIVE: 7,
        }

        return takeaways[:max_takeaways.get(level, 5)]
