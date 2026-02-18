"""Tests for report formatters."""

import pytest
from datetime import datetime

from src.reports.models import (
    Report,
    ReportConfig,
    ReportLevel,
    PulseSection,
    MacroSection,
    AssetSection,
    ForwardSection,
    MarketRegimeInfo,
    OutlierEvent,
)
from src.reports.formatters import MarkdownFormatter


@pytest.fixture
def sample_report():
    """Create a sample report for testing."""
    regime = MarketRegimeInfo(
        regime="goldilocks",
        confidence=0.78,
        description="Markets in favorable environment.",
        signals=["Low inflation", "Moderate growth"],
    )

    pulse = PulseSection(
        regime=regime,
        big_narrative="Markets are in Goldilocks mode.",
        key_takeaways=["Equity bias: Bullish", "Duration: Neutral"],
    )

    macro = MacroSection(
        global_outlook="Global economy navigating policy tightening.",
        themes=["Central bank divergence", "Geopolitical risk"],
    )

    assets = AssetSection()

    forward = ForwardSection(
        lesson_of_the_day="The trend is your friend.",
        upcoming_events=[],
        outlier_event=OutlierEvent(
            event="Fed emergency cut",
            probability="Low (5%)",
            potential_impact="Risk rally",
        ),
    )

    config = ReportConfig()

    return Report(
        report_id="TEST-001",
        title="Test Report - February 17, 2024",
        level=ReportLevel.STANDARD,
        config=config,
        pulse=pulse,
        macro=macro,
        assets=assets,
        forward=forward,
    )


class TestMarkdownFormatter:
    """Tests for MarkdownFormatter."""

    def test_format_returns_string(self, sample_report):
        """Test that format returns a string."""
        formatter = MarkdownFormatter()
        result = formatter.format(sample_report)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_contains_title(self, sample_report):
        """Test that output contains report title."""
        formatter = MarkdownFormatter()
        result = formatter.format(sample_report)

        assert sample_report.title in result

    def test_format_contains_sections(self, sample_report):
        """Test that output contains all sections."""
        formatter = MarkdownFormatter()
        result = formatter.format(sample_report)

        assert "THE PULSE" in result
        assert "MACRO ANALYSIS" in result
        assert "ASSET CLASS" in result
        assert "FORWARD WATCH" in result

    def test_format_contains_regime(self, sample_report):
        """Test that output contains regime info."""
        formatter = MarkdownFormatter()
        result = formatter.format(sample_report)

        assert "Goldilocks" in result
        assert "78%" in result

    def test_format_contains_takeaways(self, sample_report):
        """Test that output contains takeaways."""
        formatter = MarkdownFormatter()
        result = formatter.format(sample_report)

        assert "Equity bias: Bullish" in result
        assert "Duration: Neutral" in result

    def test_format_contains_themes(self, sample_report):
        """Test that output contains macro themes."""
        formatter = MarkdownFormatter()
        result = formatter.format(sample_report)

        assert "Central bank divergence" in result

    def test_format_contains_outlier(self, sample_report):
        """Test that output contains outlier event."""
        formatter = MarkdownFormatter()
        result = formatter.format(sample_report)

        assert "Fed emergency cut" in result
        assert "Low (5%)" in result

    def test_format_markdown_structure(self, sample_report):
        """Test markdown structure."""
        formatter = MarkdownFormatter()
        result = formatter.format(sample_report)

        # Check for markdown headers
        assert "# " in result
        assert "## " in result
        assert "### " in result

        # Check for emphasis
        assert "**" in result

        # Check for horizontal rules
        assert "---" in result
