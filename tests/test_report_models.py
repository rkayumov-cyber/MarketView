"""Tests for report models."""

import pytest
from datetime import datetime

from src.reports.models import (
    ReportConfig,
    ReportLevel,
    ReportFormat,
    Report,
    PulseSection,
    MacroSection,
    AssetSection,
    ForwardSection,
    MarketRegimeInfo,
    RegionMacro,
    EconomicEvent,
    OutlierEvent,
)


class TestReportConfig:
    """Tests for ReportConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ReportConfig()

        assert config.level == ReportLevel.STANDARD
        assert config.format == ReportFormat.MARKDOWN
        assert config.include_technicals is True
        assert config.include_sentiment is True
        assert config.include_correlations is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = ReportConfig(
            level=ReportLevel.EXECUTIVE,
            format=ReportFormat.PDF,
            include_technicals=False,
        )

        assert config.level == ReportLevel.EXECUTIVE
        assert config.format == ReportFormat.PDF
        assert config.include_technicals is False


class TestReportLevel:
    """Tests for ReportLevel enum."""

    def test_level_values(self):
        """Test report level values."""
        assert ReportLevel.EXECUTIVE == 1
        assert ReportLevel.STANDARD == 2
        assert ReportLevel.DEEP_DIVE == 3


class TestMarketRegimeInfo:
    """Tests for MarketRegimeInfo."""

    def test_create_regime_info(self):
        """Test creating regime info."""
        info = MarketRegimeInfo(
            regime="goldilocks",
            confidence=0.78,
            description="Test description",
            signals=["Signal 1", "Signal 2"],
        )

        assert info.regime == "goldilocks"
        assert info.confidence == 0.78
        assert len(info.signals) == 2


class TestPulseSection:
    """Tests for PulseSection."""

    def test_create_pulse_section(self):
        """Test creating pulse section."""
        regime = MarketRegimeInfo(
            regime="goldilocks",
            confidence=0.78,
            description="Test",
            signals=[],
        )

        pulse = PulseSection(
            regime=regime,
            big_narrative="Test narrative",
            key_takeaways=["Takeaway 1"],
        )

        assert pulse.regime.regime == "goldilocks"
        assert pulse.big_narrative == "Test narrative"
        assert len(pulse.key_takeaways) == 1


class TestMacroSection:
    """Tests for MacroSection."""

    def test_create_macro_section(self):
        """Test creating macro section."""
        us = RegionMacro(
            region="US",
            headline="Test headline",
            risks=["Risk 1"],
            opportunities=["Opportunity 1"],
        )

        macro = MacroSection(
            us=us,
            global_outlook="Test outlook",
            themes=["Theme 1"],
        )

        assert macro.us.region == "US"
        assert macro.global_outlook == "Test outlook"


class TestForwardSection:
    """Tests for ForwardSection."""

    def test_create_forward_section(self):
        """Test creating forward section."""
        event = EconomicEvent(
            date="2024-05-01",
            event="FOMC Decision",
            importance="high",
            expected_impact="Sets policy direction",
        )

        outlier = OutlierEvent(
            event="Test event",
            probability="Low",
            potential_impact="High impact",
        )

        forward = ForwardSection(
            lesson_of_the_day="Test lesson",
            upcoming_events=[event],
            outlier_event=outlier,
        )

        assert forward.lesson_of_the_day == "Test lesson"
        assert len(forward.upcoming_events) == 1
        assert forward.outlier_event.event == "Test event"


class TestReport:
    """Tests for Report model."""

    def test_create_minimal_report(self):
        """Test creating a minimal report."""
        regime = MarketRegimeInfo(
            regime="goldilocks",
            confidence=0.78,
            description="Test",
            signals=[],
        )

        pulse = PulseSection(
            regime=regime,
            big_narrative="Test",
            key_takeaways=[],
        )

        macro = MacroSection(
            global_outlook="Test",
            themes=[],
        )

        assets = AssetSection()

        forward = ForwardSection(
            lesson_of_the_day="Test",
            upcoming_events=[],
            outlier_event=OutlierEvent(
                event="Test",
                probability="Low",
                potential_impact="Test",
            ),
        )

        config = ReportConfig()

        report = Report(
            report_id="TEST-001",
            title="Test Report",
            level=ReportLevel.STANDARD,
            config=config,
            pulse=pulse,
            macro=macro,
            assets=assets,
            forward=forward,
        )

        assert report.report_id == "TEST-001"
        assert report.level == ReportLevel.STANDARD
        assert report.pulse.regime.regime == "goldilocks"

    def test_report_to_dict(self):
        """Test report serialization."""
        regime = MarketRegimeInfo(
            regime="goldilocks",
            confidence=0.78,
            description="Test",
            signals=[],
        )

        pulse = PulseSection(
            regime=regime,
            big_narrative="Test",
            key_takeaways=[],
        )

        macro = MacroSection(
            global_outlook="Test",
            themes=[],
        )

        assets = AssetSection()

        forward = ForwardSection(
            lesson_of_the_day="Test",
            upcoming_events=[],
            outlier_event=OutlierEvent(
                event="Test",
                probability="Low",
                potential_impact="Test",
            ),
        )

        config = ReportConfig()

        report = Report(
            report_id="TEST-001",
            title="Test Report",
            level=ReportLevel.STANDARD,
            config=config,
            pulse=pulse,
            macro=macro,
            assets=assets,
            forward=forward,
        )

        data = report.to_dict()

        assert "report_id" in data
        assert "title" in data
        assert "pulse" in data
        assert "macro" in data
        assert "assets" in data
        assert "forward" in data
