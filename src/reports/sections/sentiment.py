"""Sentiment section builder - Dedicated social sentiment analysis."""

from src.ingestion.tier2_sentiment import RedditClient
from src.reports.models import (
    SentimentSection,
    SubredditBreakdown,
    ReportLevel,
)


class SentimentSectionBuilder:
    """Builder for the Sentiment analysis section."""

    def __init__(self) -> None:
        self.reddit = RedditClient()

    async def build(self, level: ReportLevel) -> SentimentSection:
        """Build the Sentiment section."""
        all_sentiment = await self.reddit.get_all_sentiment()
        overall = await self.reddit.get_overall_sentiment()

        if "error" in overall:
            return self._build_fallback()

        overall_score = overall.get("overall_sentiment", 0.0)
        bullish_ratio = overall.get("overall_bullish_ratio", 0.5)
        total_posts = overall.get("total_posts_analyzed", 0)
        subreddit_count = overall.get("subreddit_count", 0)
        trending = overall.get("trending_tickers", [])

        # Per-subreddit breakdowns (L2+)
        breakdowns = []
        if level >= ReportLevel.STANDARD and all_sentiment:
            for name, data in all_sentiment.items():
                breakdowns.append(SubredditBreakdown(
                    subreddit=name,
                    sentiment_score=data.sentiment_score,
                    bullish_ratio=data.bullish_ratio,
                    post_count=data.post_count,
                    top_tickers=data.top_tickers[:5],
                ))
            breakdowns.sort(key=lambda b: abs(b.sentiment_score), reverse=True)

        # Label
        overall_label = self._score_label(overall_score)

        # Narrative
        narrative = self._generate_narrative(
            overall_score, bullish_ratio, trending, breakdowns, level
        )

        # Contrarian signals (L2+)
        contrarian = []
        if level >= ReportLevel.STANDARD:
            contrarian = self._detect_contrarian(breakdowns, overall_score)

        return SentimentSection(
            overall_score=overall_score,
            overall_label=overall_label,
            bullish_ratio=bullish_ratio,
            total_posts=total_posts,
            subreddit_count=subreddit_count,
            trending_tickers=trending[:10],
            subreddit_breakdowns=breakdowns,
            narrative=narrative,
            contrarian_signals=contrarian,
        )

    def _score_label(self, score: float) -> str:
        if score > 0.2:
            return "Bullish"
        if score < -0.2:
            return "Bearish"
        return "Neutral"

    def _generate_narrative(
        self,
        score: float,
        bullish_ratio: float,
        trending: list[tuple[str, int]],
        breakdowns: list[SubredditBreakdown],
        level: ReportLevel,
    ) -> str:
        label = self._score_label(score)
        parts = [
            f"Retail sentiment across financial Reddit is **{label.lower()}** "
            f"with an overall score of {score:+.2f} and {bullish_ratio:.0%} "
            f"of posts leaning bullish."
        ]

        if trending:
            top = [f"${t[0]}" for t in trending[:5]]
            parts.append(f"Most-discussed tickers: {', '.join(top)}.")

        if level >= ReportLevel.STANDARD and breakdowns:
            most_bullish = max(breakdowns, key=lambda b: b.sentiment_score)
            most_bearish = min(breakdowns, key=lambda b: b.sentiment_score)
            if most_bullish.sentiment_score > 0:
                parts.append(
                    f"r/{most_bullish.subreddit} is the most bullish community "
                    f"({most_bullish.sentiment_score:+.2f})."
                )
            if most_bearish.sentiment_score < 0:
                parts.append(
                    f"r/{most_bearish.subreddit} tilts most bearish "
                    f"({most_bearish.sentiment_score:+.2f})."
                )

        return " ".join(parts)

    def _detect_contrarian(
        self,
        breakdowns: list[SubredditBreakdown],
        overall_score: float,
    ) -> list[str]:
        signals = []

        # Extreme bullishness is contrarian-bearish
        if overall_score > 0.5:
            signals.append(
                "Extreme bullish consensus — historically a contrarian sell signal"
            )
        elif overall_score < -0.5:
            signals.append(
                "Extreme bearish consensus — historically a contrarian buy signal"
            )

        # Divergence between communities
        if len(breakdowns) >= 2:
            scores = [b.sentiment_score for b in breakdowns]
            spread = max(scores) - min(scores)
            if spread > 0.6:
                signals.append(
                    f"Wide sentiment dispersion across communities (spread: {spread:.2f}) "
                    f"— suggests market uncertainty and potential for sharp moves"
                )

        return signals

    def _build_fallback(self) -> SentimentSection:
        return SentimentSection(
            overall_score=0.0,
            overall_label="Unavailable",
            bullish_ratio=0.5,
            total_posts=0,
            subreddit_count=0,
            narrative="Sentiment data is currently unavailable. "
            "Reddit API may be unconfigured or rate-limited.",
            source="reddit",
        )
