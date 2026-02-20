"""Reddit sentiment analysis client using public JSON API (no auth required)."""

import asyncio
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from src.config.constants import REDDIT_SUBREDDITS
from src.config.settings import settings

logger = logging.getLogger(__name__)


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
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

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


# ── In-memory TTL cache (same pattern as twelve_data_client) ──

class _MemCache:
    def __init__(self, ttl: int = 300):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry and (time.monotonic() - entry[0]) < self._ttl:
            return entry[1]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic(), value)


_cache = _MemCache(ttl=settings.cache_ttl_reddit)


class RedditClient:
    """Reddit client using public JSON API — no credentials required."""

    # Ticker pattern: $SYMBOL or standalone 2-5 letter uppercase
    TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b")

    COMMON_WORDS = frozenset({
        "I", "A", "THE", "TO", "AND", "OR", "FOR", "IS", "IT", "DD", "OP",
        "CEO", "CFO", "IPO", "ETF", "GDP", "CPI", "FED", "SEC", "US", "UK",
        "EU", "AI", "PM", "AM", "AT", "IN", "ON", "BY", "UP", "IF", "SO",
        "MY", "HE", "WE", "DO", "NO", "AS", "OF", "IMO", "TBH", "PSA",
        "RIP", "LOL", "WTF", "OMG", "FYI", "AMA", "ELI", "EDIT", "TLDR",
        "NEW", "ALL", "ANY", "NOW", "OUT", "HAS", "NOT", "BUT", "ARE",
        "HOW", "WHY", "JUST", "WHAT", "WHEN", "THIS", "THAT", "WITH",
        "FROM", "WILL", "HAVE", "BEEN", "THEY", "VERY", "MOST", "SOME",
        "THAN", "OVER", "LIKE", "ONLY", "ALSO", "MORE", "MUCH", "HERE",
        "HIGH", "LOW", "GOOD", "BEST", "LAST", "NEXT", "LONG", "FREE",
        # Options / trading jargon (not tickers)
        "IV", "DTE", "ITM", "OTM", "ATM", "CSP", "CC", "PMCC", "LEAP",
        "YOY", "QOQ", "MOM", "PE", "PB", "PS", "EPS", "NAV", "AUM",
        "FAQ", "IQ", "QR", "GL", "PLC", "DA", "LD", "SD", "LU", "SU",
        "ERC", "EIP", "EIPS", "BIP", "MPC", "AA", "VIP", "SMS", "GMT",
        "NFL", "GPU", "CUDA", "WASM", "ECDSA", "OWASP", "HODL", "SELL",
        "SPAC", "UMAC", "FOCIL", "EF", "USD", "EUR", "GBP", "JPY", "CAD",
        "BUY", "CALL", "PUT", "ETF", "REIT", "CEO", "COO", "CTO",
    })

    BULLISH_KEYWORDS = [
        "buy", "calls", "moon", "rocket", "bullish", "long", "yolo",
        "tendies", "gain", "pump", "breakout", "squeeze", "diamond hands",
        "hold", "hodl", "to the moon", "going up", "undervalued",
        "rally", "rip", "green", "soar", "surge",
    ]
    BEARISH_KEYWORDS = [
        "sell", "puts", "crash", "bearish", "short", "dump", "tank",
        "loss", "drop", "overvalued", "bubble", "paper hands",
        "going down", "red", "blood", "correction", "plunge",
        "bear", "fade", "drill",
    ]

    _HEADERS = {
        "User-Agent": settings.reddit_user_agent,
    }

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            headers=self._HEADERS,
            timeout=15.0,
            follow_redirects=True,
        )

    # ── Public JSON API ────────────────────────────────────────

    async def _fetch_subreddit_json(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 50,
        t: str = "day",
    ) -> list[dict]:
        """Fetch posts from Reddit's public JSON API."""
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
        params: dict[str, Any] = {"limit": limit, "raw_json": 1}
        if sort == "top":
            params["t"] = t

        try:
            resp = await self._http.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            return [c["data"] for c in children if c.get("kind") == "t3"]
        except Exception as e:
            logger.warning("Failed to fetch r/%s: %s", subreddit, e)
            return []

    # ── Ticker / sentiment helpers ─────────────────────────────

    def _extract_tickers(self, text: str) -> list[str]:
        matches = self.TICKER_PATTERN.findall(text)
        seen: set[str] = set()
        tickers = []
        for match in matches:
            ticker = match[0] or match[1]
            if ticker not in self.COMMON_WORDS and ticker not in seen:
                tickers.append(ticker)
                seen.add(ticker)
        return tickers

    def _analyze_sentiment(self, text: str) -> float:
        text_lower = text.lower()
        bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text_lower)
        bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text_lower)
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0
        return (bullish_count - bearish_count) / total

    # ── Core public methods ────────────────────────────────────

    async def fetch_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 50,
        time_filter: str = "day",
    ) -> list[RedditPost]:
        """Fetch posts from a subreddit via public JSON API."""
        raw_posts = await self._fetch_subreddit_json(
            subreddit_name, sort="hot", limit=limit, t=time_filter,
        )

        posts = []
        for p in raw_posts:
            text = f"{p.get('title', '')} {p.get('selftext', '')}"
            tickers = self._extract_tickers(text)
            posts.append(RedditPost(
                title=p.get("title", ""),
                subreddit=subreddit_name,
                score=p.get("score", 0),
                num_comments=p.get("num_comments", 0),
                created_utc=datetime.fromtimestamp(p.get("created_utc", 0), tz=UTC),
                url=f"https://reddit.com{p.get('permalink', '')}",
                is_self=p.get("is_self", False),
                selftext=(p.get("selftext", "") or "")[:500],
                tickers=tickers,
            ))
        return posts

    async def analyze_subreddit(
        self,
        subreddit_name: str,
        limit: int = 50,
    ) -> SubredditSentiment | None:
        """Analyze sentiment for a subreddit."""
        posts = await self.fetch_subreddit_posts(subreddit_name, limit)
        if not posts:
            return None

        total_score = sum(p.score for p in posts)
        total_comments = sum(p.num_comments for p in posts)

        all_tickers: list[str] = []
        for p in posts:
            all_tickers.extend(p.tickers)
        ticker_counts = Counter(all_tickers).most_common(10)

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
        """Get sentiment from all configured subreddits (cached)."""
        cached = _cache.get("all_sentiment")
        if cached is not None:
            return cached

        tasks = [self.analyze_subreddit(sub) for sub in REDDIT_SUBREDDITS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        sentiment_data: dict[str, SubredditSentiment] = {}
        for sub, result in zip(REDDIT_SUBREDDITS, results):
            if isinstance(result, SubredditSentiment):
                sentiment_data[sub] = result
            elif isinstance(result, Exception):
                logger.warning("Error analyzing r/%s: %s", sub, result)

        if sentiment_data:
            _cache.set("all_sentiment", sentiment_data)
        return sentiment_data

    async def get_trending_tickers(self, limit: int = 20) -> list[tuple[str, int]]:
        """Get trending tickers across all subreddits."""
        sentiment_data = await self.get_all_sentiment()
        all_tickers: Counter[str] = Counter()
        for data in sentiment_data.values():
            for ticker, count in data.top_tickers:
                all_tickers[ticker] += count
        return all_tickers.most_common(limit)

    async def get_overall_sentiment(self) -> dict[str, Any]:
        """Get overall market sentiment summary."""
        sentiment_data = await self.get_all_sentiment()
        if not sentiment_data:
            return {}

        total_posts = sum(d.post_count for d in sentiment_data.values())
        if total_posts == 0:
            return {}

        weighted_sentiment = sum(
            d.sentiment_score * d.post_count for d in sentiment_data.values()
        ) / total_posts

        weighted_bullish = sum(
            d.bullish_ratio * d.post_count for d in sentiment_data.values()
        ) / total_posts

        trending = await self.get_trending_tickers(10)

        return {
            "overall_sentiment": round(weighted_sentiment, 4),
            "overall_bullish_ratio": round(weighted_bullish, 4),
            "total_posts_analyzed": total_posts,
            "subreddit_count": len(sentiment_data),
            "trending_tickers": trending,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def health_check(self) -> bool:
        """Check Reddit public API availability."""
        try:
            resp = await self._http.get(
                "https://www.reddit.com/r/stocks/hot.json",
                params={"limit": 1, "raw_json": 1},
            )
            return resp.status_code == 200
        except Exception:
            return False
