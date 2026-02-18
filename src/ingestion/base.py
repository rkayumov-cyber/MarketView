"""Base classes for data ingestion."""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

import redis.asyncio as redis

from src.config.settings import settings
from src.ingestion.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheManager:
    """Redis-based cache manager."""

    _instance: "CacheManager | None" = None
    _redis: redis.Redis | None = None

    def __new__(cls) -> "CacheManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    @staticmethod
    def _make_key(prefix: str, *args: Any, **kwargs: Any) -> str:
        """Generate a cache key from arguments."""
        key_parts = [prefix] + [str(a) for a in args]
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(hashlib.md5(str(sorted_kwargs).encode()).hexdigest()[:8])
        return ":".join(key_parts)

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self._redis:
            await self.connect()

        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        if not self._redis:
            await self.connect()

        try:
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._redis:
            await self.connect()

        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    async def clear_prefix(self, prefix: str) -> int:
        """Clear all keys with given prefix."""
        if not self._redis:
            await self.connect()

        try:
            keys = []
            async for key in self._redis.scan_iter(f"{prefix}:*"):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"Cache clear error for prefix {prefix}: {e}")
            return 0


class DataSource(ABC, Generic[T]):
    """Abstract base class for data sources.

    Provides caching and rate limiting infrastructure.
    """

    source_name: str = "base"
    cache_ttl: int = 3600
    rate_limit: int = 60  # requests per minute

    def __init__(self) -> None:
        self.cache = CacheManager()
        self.rate_limiter = RateLimiter.from_per_minute(self.rate_limit)
        self.logger = logging.getLogger(f"datasource.{self.source_name}")

    def _cache_key(self, method: str, *args: Any, **kwargs: Any) -> str:
        """Generate cache key for a method call."""
        return CacheManager._make_key(self.source_name, method, *args, **kwargs)

    async def _with_cache(
        self,
        method: str,
        fetch_func: Any,
        *args: Any,
        ttl: int | None = None,
        **kwargs: Any,
    ) -> T | None:
        """Execute with caching support.

        Args:
            method: Method name for cache key
            fetch_func: Async function to fetch data
            *args: Arguments for cache key and fetch function
            ttl: Custom TTL (defaults to source cache_ttl)
            **kwargs: Keyword arguments for cache key and fetch function

        Returns:
            Cached or freshly fetched data
        """
        cache_key = self._cache_key(method, *args, **kwargs)
        ttl = ttl or self.cache_ttl

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached is not None:
            self.logger.debug(f"Cache hit: {cache_key}")
            return cached

        # Rate limit and fetch
        await self.rate_limiter.acquire()

        try:
            # fetch_func is a closure that captures its own arguments
            data = await fetch_func()
            if data is not None:
                await self.cache.set(cache_key, data, ttl)
            return data
        except Exception as e:
            self.logger.error(f"Fetch error for {method}: {e}")
            raise

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if data source is available."""
        ...

    @abstractmethod
    async def fetch_latest(self) -> T | None:
        """Fetch latest data from source."""
        ...


class DataPoint:
    """Base class for data points with timestamp."""

    def __init__(
        self,
        value: float,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.value = value
        self.timestamp = timestamp or datetime.now(UTC)
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DataPoint":
        return cls(
            value=data["value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )
