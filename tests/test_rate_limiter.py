"""Tests for rate limiter."""

import asyncio
import pytest

from src.ingestion.rate_limiter import RateLimiter, RateLimiterRegistry


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_create_from_per_minute(self):
        """Test creating rate limiter from requests per minute."""
        limiter = RateLimiter.from_per_minute(60)

        assert limiter.rate == 1.0  # 60/60 = 1 per second
        assert limiter.capacity == 60.0
        assert limiter.tokens == 60.0

    def test_try_acquire_success(self):
        """Test successful token acquisition."""
        limiter = RateLimiter.from_per_minute(60)

        assert limiter.try_acquire() is True
        assert limiter.tokens == 59.0

    def test_try_acquire_failure(self):
        """Test failed token acquisition when depleted."""
        limiter = RateLimiter(rate=1.0, capacity=1.0)
        limiter.tokens = 0

        assert limiter.try_acquire() is False

    @pytest.mark.asyncio
    async def test_acquire_with_wait(self):
        """Test async acquisition with wait."""
        limiter = RateLimiter(rate=10.0, capacity=10.0)  # Fast for testing
        limiter.tokens = 0

        # Should wait for refill
        wait_time = await limiter.acquire()
        assert wait_time > 0

    def test_available_tokens(self):
        """Test available tokens property."""
        limiter = RateLimiter.from_per_minute(60)
        limiter.try_acquire()
        limiter.try_acquire()

        assert limiter.available_tokens < 60


class TestRateLimiterRegistry:
    """Tests for RateLimiterRegistry."""

    def test_get_creates_new(self):
        """Test getting a new rate limiter."""
        RateLimiterRegistry.reset()
        limiter = RateLimiterRegistry.get("test", 60)

        assert limiter is not None
        assert limiter.capacity == 60.0

    def test_get_returns_existing(self):
        """Test getting existing rate limiter."""
        RateLimiterRegistry.reset()
        limiter1 = RateLimiterRegistry.get("test", 60)
        limiter2 = RateLimiterRegistry.get("test", 120)  # Different rate ignored

        assert limiter1 is limiter2

    def test_reset_single(self):
        """Test resetting a single limiter."""
        RateLimiterRegistry.reset()
        RateLimiterRegistry.get("test1", 60)
        RateLimiterRegistry.get("test2", 60)

        RateLimiterRegistry.reset("test1")

        # test1 should be new, test2 should be same
        limiter2 = RateLimiterRegistry.get("test2", 60)
        assert limiter2.capacity == 60.0

    def test_reset_all(self):
        """Test resetting all limiters."""
        RateLimiterRegistry.get("test1", 60)
        RateLimiterRegistry.get("test2", 60)

        RateLimiterRegistry.reset()

        # Both should be new
        assert RateLimiterRegistry._limiters == {}
