"""Reddit sentiment analysis client using PRAW."""

import asyncio
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import praw

from src.config.constants import REDDIT_SUBREDDITS
from src.config.settings import settings
from src.ingestion.base import DataSource


@dataclass
class RedditPost:
    """Reddit post data."""

    title: str
    subreddit: str
    score: int
    num_comments: int
    created_utc: datetime
    url: str
    is_self: bool
    selftext: str = ""
    tickers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subreddit": self.subreddit,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc.isoformat(),
            "url": self.url,
            "is_self": self.is_self,
            "tickers": self.tickers,
        }


@dataclass
class SubredditSentiment:
    """Sentiment data for a subreddit."""

    subreddit: str
    post_count: int
    avg_score: float
    avg_comments: float
    top_tickers: list[tuple[str, int]]
    sentiment_score: float  # -1 to 1
    bullish_ratio: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subreddit": self.subreddit,
            "post_count": self.post_count,
            "avg_score": self.avg_score,
            "avg_comments": self.avg_comments,
            "top_tickers": self.top_tickers,
            "sentiment_score": self.sentiment_score,
            "bullish_ratio": self.bullish_ratio,
            "timestamp": self.timestamp.isoformat(),
        }


class RedditClient(DataSource[dict[str, SubredditSentiment]]):
    """Reddit API client for sentiment analysis."""

    source_name = "reddit"
    cache_ttl = settings.cache_ttl_reddit
    rate_limit = settings.rate_limit_reddit

    # Ticker pattern: $SYMBOL or standalone 2-5 letter uppercase
    TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b")

    # Sentiment keywords
    BULLISH_KEYWORDS = [
        "buy", "calls", "moon", "rocket", "bullish", "long", "yolo",
        "tendies", "gain", "pump", "breakout", "squeeze", "diamond hands",
        "hold", "hodl", "to the moon", "going up", "undervalued",
    ]
    BEARISH_KEYWORDS = [
        "sell", "puts", "crash", "bearish", "short", "dump", "tank",
        "loss", "drop", "overvalued", "bubble", "puts", "paper hands",
        "going down", "red", "blood", "rip", "correction",
    ]

    def __init__(self) -> None:
        super().__init__()
        client_id = settings.reddit_client_id
        client_secret = settings.reddit_client_secret

        if client_id and client_secret:
            self._client = praw.Reddit(
                client_id=client_id.get_secret_value(),
                client_secret=client_secret.get_secret_value(),
                user_agent=settings.reddit_user_agent,
            )
        else:
            self._client = None
            self.logger.warning("Reddit API credentials not configured")

    async def health_check(self) -> bool:
        """Check Reddit API availability."""
        if not self._client:
            return False
        try:
            await asyncio.to_thread(lambda: self._client.subreddit("test").id)
            return True
        except Exception as e:
            self.logger.error(f"Reddit health check failed: {e}")
            return False

    async def fetch_latest(self) -> dict[str, SubredditSentiment] | None:
        """Fetch sentiment from all configured subreddits."""
        return await self.get_all_sentiment()

    def _extract_tickers(self, text: str) -> list[str]:
        """Extract stock tickers from text."""
        matches = self.TICKER_PATTERN.findall(text)
        tickers = []
        for match in matches:
            ticker = match[0] or match[1]
            # Filter common words
            if ticker not in {"I", "A", "THE", "TO", "AND", "OR", "FOR", "IS", "IT", "DD", "OP", "CEO", "CFO", "IPO", "ETF", "GDP", "CPI", "FED", "SEC"}:
                tickers.append(ticker)
        return tickers

    def _analyze_sentiment(self, text: str) -> float:
        """Simple keyword-based sentiment analysis.

        Returns:
            Sentiment score from -1 (bearish) to 1 (bullish)
        """
        text_lower = text.lower()

        bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text_lower)
        bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text_lower)

        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        return (bullish_count - bearish_count) / total

    async def fetch_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 100,
        time_filter: str = "day",
    ) -> list[RedditPost]:
        """Fetch top posts from a subreddit."""
        if not self._client:
            self.logger.error("Reddit client not initialized")
            return []

        async def _fetch() -> list[RedditPost]:
            try:
                subreddit = self._client.subreddit(subreddit_name)
                posts = []

                for submission in subreddit.top(time_filter=time_filter, limit=limit):
                    text = f"{submission.title} {submission.selftext}"
                    tickers = self._extract_tickers(text)

                    posts.append(RedditPost(
                        title=submission.title,
                        subreddit=subreddit_name,
                        score=submission.score,
                        num_comments=submission.num_comments,
                        created_utc=datetime.utcfromtimestamp(submission.created_utc),
                        url=f"https://reddit.com{submission.permalink}",
                        is_self=submission.is_self,
                        selftext=submission.selftext[:500] if submission.selftext else "",
                        tickers=tickers,
                    ))

                return posts
            except Exception as e:
                self.logger.error(f"Error fetching r/{subreddit_name}: {e}")
                return []

        # Run synchronous PRAW in thread pool
        return await asyncio.to_thread(_fetch)

    async def analyze_subreddit(
        self,
        subreddit_name: str,
        limit: int = 100,
    ) -> SubredditSentiment | None:
        """Analyze sentiment for a subreddit."""
        posts = await self.fetch_subreddit_posts(subreddit_name, limit)

        if not posts:
            return None

        # Aggregate metrics
        total_score = sum(p.score for p in posts)
        total_comments = sum(p.num_comments for p in posts)

        # Ticker frequency
        all_tickers: list[str] = []
        for p in posts:
            all_tickers.extend(p.tickers)
        ticker_counts = Counter(all_tickers).most_common(10)

        # Sentiment analysis
        sentiments = []
        for p in posts:
            text = f"{p.title} {p.selftext}"
            sentiments.append(self._analyze_sentiment(text))

        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        bullish_count = sum(1 for s in sentiments if s > 0)
        bullish_ratio = bullish_count / len(sentiments) if sentiments else 0.5

        return SubredditSentiment(
            subreddit=subreddit_name,
            post_count=len(posts),
            avg_score=total_score / len(posts),
            avg_comments=total_comments / len(posts),
            top_tickers=ticker_counts,
            sentiment_score=avg_sentiment,
            bullish_ratio=bullish_ratio,
        )

    async def get_all_sentiment(self) -> dict[str, SubredditSentiment]:
        """Get sentiment from all configured subreddits."""
        async def _fetch_all() -> dict[str, SubredditSentiment]:
            tasks = [
                self.analyze_subreddit(sub)
                for sub in REDDIT_SUBREDDITS
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            sentiment_data = {}
            for sub, result in zip(REDDIT_SUBREDDITS, results):
                if isinstance(result, SubredditSentiment):
                    sentiment_data[sub] = result
                elif isinstance(result, Exception):
                    self.logger.error(f"Error analyzing r/{sub}: {result}")

            return sentiment_data

        return await self._with_cache("get_all_sentiment", _fetch_all)

    async def get_trending_tickers(self, limit: int = 20) -> list[tuple[str, int]]:
        """Get trending tickers across all subreddits."""
        sentiment_data = await self.get_all_sentiment()

        # Aggregate ticker counts
        all_tickers: Counter[str] = Counter()
        for data in sentiment_data.values():
            for ticker, count in data.top_tickers:
                all_tickers[ticker] += count

        return all_tickers.most_common(limit)

    async def get_overall_sentiment(self) -> dict[str, Any]:
        """Get overall market sentiment summary."""
        sentiment_data = await self.get_all_sentiment()

        if not sentiment_data:
            return {"error": "No sentiment data available"}

        # Weighted average by post count
        total_posts = sum(d.post_count for d in sentiment_data.values())
        if total_posts == 0:
            return {"error": "No posts found"}

        weighted_sentiment = sum(
            d.sentiment_score * d.post_count for d in sentiment_data.values()
        ) / total_posts

        weighted_bullish = sum(
            d.bullish_ratio * d.post_count for d in sentiment_data.values()
        ) / total_posts

        trending = await self.get_trending_tickers(10)

        return {
            "overall_sentiment": weighted_sentiment,
            "overall_bullish_ratio": weighted_bullish,
            "total_posts_analyzed": total_posts,
            "subreddit_count": len(sentiment_data),
            "trending_tickers": trending,
            "timestamp": datetime.utcnow().isoformat(),
        }
