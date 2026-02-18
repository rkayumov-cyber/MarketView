"""Report builder - orchestrates report generation."""

import asyncio
import uuid
from datetime import UTC, datetime

from src.reports.models import Report, ReportConfig, ReportLevel
from src.reports.sections import (
    PulseSectionBuilder,
    MacroSectionBuilder,
    AssetSectionBuilder,
    TechnicalsSectionBuilder,
    ForwardSectionBuilder,
)


class ReportBuilder:
    """Orchestrates the building of complete reports."""

    def __init__(self) -> None:
        self.pulse_builder = PulseSectionBuilder()
        self.macro_builder = MacroSectionBuilder()
        self.asset_builder = AssetSectionBuilder()
        self.technicals_builder = TechnicalsSectionBuilder()
        self.forward_builder = ForwardSectionBuilder()

    async def build(self, config: ReportConfig | None = None) -> Report:
        """Build a complete report.

        Args:
            config: Report configuration

        Returns:
            Complete Report object
        """
        if config is None:
            config = ReportConfig()

        level = config.level

        # Generate report ID
        report_id = f"RPT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

        # Build sections concurrently where possible
        pulse_task = self.pulse_builder.build(level)
        macro_task = self.macro_builder.build(level)
        asset_task = self.asset_builder.build(level)
        forward_task = self.forward_builder.build(level)

        # Technicals is optional
        technicals_task = None
        if config.include_technicals:
            technicals_task = self.technicals_builder.build(level)

        # Gather results
        results = await asyncio.gather(
            pulse_task,
            macro_task,
            asset_task,
            forward_task,
            return_exceptions=True,
        )

        pulse, macro, assets, forward = results

        # Handle any errors
        if isinstance(pulse, Exception):
            raise RuntimeError(f"Failed to build Pulse section: {pulse}")
        if isinstance(macro, Exception):
            raise RuntimeError(f"Failed to build Macro section: {macro}")
        if isinstance(assets, Exception):
            raise RuntimeError(f"Failed to build Assets section: {assets}")
        if isinstance(forward, Exception):
            raise RuntimeError(f"Failed to build Forward section: {forward}")

        # Get technicals if requested
        technicals = None
        if technicals_task:
            try:
                technicals = await technicals_task
            except Exception as e:
                print(f"Warning: Failed to build Technicals section: {e}")

        # Generate title
        title = config.title or self._generate_title(level, pulse)

        return Report(
            report_id=report_id,
            title=title,
            level=level,
            config=config,
            pulse=pulse,
            macro=macro,
            assets=assets,
            technicals=technicals,
            forward=forward,
            metadata={
                "generated_at": datetime.now(UTC).isoformat(),
                "version": "1.0",
            },
        )

    def _generate_title(self, level: ReportLevel, pulse) -> str:
        """Generate report title based on content."""
        date_str = datetime.now(UTC).strftime("%B %d, %Y")
        regime = pulse.regime.regime.replace("_", " ").title()

        level_names = {
            ReportLevel.EXECUTIVE: "Executive Brief",
            ReportLevel.STANDARD: "Daily Alpha Brief",
            ReportLevel.DEEP_DIVE: "Deep Dive Analysis",
        }

        level_name = level_names.get(level, "Market Report")

        return f"{level_name}: {regime} - {date_str}"

    async def build_quick(self) -> Report:
        """Build a quick executive-level report."""
        config = ReportConfig(
            level=ReportLevel.EXECUTIVE,
            include_technicals=False,
            include_correlations=False,
        )
        return await self.build(config)

    async def build_standard(self) -> Report:
        """Build a standard daily report."""
        config = ReportConfig(level=ReportLevel.STANDARD)
        return await self.build(config)

    async def build_deep_dive(self) -> Report:
        """Build a comprehensive deep dive report."""
        config = ReportConfig(
            level=ReportLevel.DEEP_DIVE,
            include_technicals=True,
            include_correlations=True,
        )
        return await self.build(config)
