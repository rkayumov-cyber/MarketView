"""Pytest configuration and fixtures."""

import asyncio
import pytest
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_price_data():
    """Generate sample OHLCV data for testing."""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    dates = pd.date_range(end=datetime.now(), periods=250, freq="D")

    # Generate random walk price data
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.015, len(dates))
    prices = 100 * np.cumprod(1 + returns)

    df = pd.DataFrame({
        "Open": prices * (1 + np.random.normal(0, 0.005, len(dates))),
        "High": prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
        "Low": prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
        "Close": prices,
        "Volume": np.random.randint(1000000, 10000000, len(dates)),
    }, index=dates)

    return df


@pytest.fixture
def sample_report_config():
    """Sample report configuration."""
    from src.reports.models import ReportConfig, ReportLevel

    return ReportConfig(
        level=ReportLevel.STANDARD,
        include_technicals=True,
        include_sentiment=True,
        include_correlations=False,
    )
