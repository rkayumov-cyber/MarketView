"""Token bucket rate limiter for API calls."""

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Token bucket rate limiter.

    Attributes:
        rate: Maximum requests per second
        capacity: Maximum tokens in bucket
        tokens: Current token count
        last_update: Last token update timestamp
    """

    rate: float  # tokens per second
    capacity: float
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self.last_update = time.monotonic()

    @classmethod
    def from_per_minute(cls, requests_per_minute: int) -> "RateLimiter":
        """Create rate limiter from requests per minute."""
        rate = requests_per_minute / 60.0
        return cls(rate=rate, capacity=float(requests_per_minute))

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    async def acquire(self, tokens: float = 1.0) -> float:
        """Acquire tokens, waiting if necessary.

        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0

            # Calculate wait time
            deficit = tokens - self.tokens
            wait_time = deficit / self.rate

            # Wait and refill
            await asyncio.sleep(wait_time)
            self._refill()
            self.tokens -= tokens

            return wait_time

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """Try to acquire tokens without waiting.

        Returns:
            True if tokens acquired, False otherwise
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        self._refill()
        return self.tokens


class RateLimiterRegistry:
    """Registry for managing multiple rate limiters."""

    _limiters: dict[str, RateLimiter] = {}

    @classmethod
    def get(cls, name: str, requests_per_minute: int = 60) -> RateLimiter:
        """Get or create a rate limiter by name."""
        if name not in cls._limiters:
            cls._limiters[name] = RateLimiter.from_per_minute(requests_per_minute)
        return cls._limiters[name]

    @classmethod
    def reset(cls, name: str | None = None) -> None:
        """Reset one or all rate limiters."""
        if name:
            cls._limiters.pop(name, None)
        else:
            cls._limiters.clear()
