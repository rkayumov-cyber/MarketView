"""Macro section builder."""

from src.analysis import MacroAnalyzer
from src.reports.models import (
    MacroSection,
    RegionMacro,
    ReportLevel,
)


class MacroSectionBuilder:
    """Builder for the Macro analysis section."""

    def __init__(self) -> None:
        self.analyzer = MacroAnalyzer()

    async def build(self, level: ReportLevel) -> MacroSection:
        """Build the Macro section."""
        # Get full macro analysis
        analysis = await self.analyzer.full_analysis()

        # Build US section
        us = self._build_region_macro(analysis.us, level) if analysis.us else None

        # Build EU section (simplified for now)
        eu = self._build_region_macro(analysis.eu, level) if analysis.eu else None

        # Build Asia section (simplified for now)
        asia = self._build_region_macro(analysis.asia, level) if analysis.asia else None

        return MacroSection(
            us=us,
            eu=eu,
            asia=asia,
            global_outlook=analysis.global_outlook,
            themes=analysis.cross_regional_themes[:5] if level >= ReportLevel.STANDARD else analysis.cross_regional_themes[:3],
        )

    def _build_region_macro(
        self,
        regional: "RegionalAnalysis",  # noqa: F821
        level: ReportLevel,
    ) -> RegionMacro:
        """Build regional macro summary."""
        # Generate headline
        headline = regional.overall_assessment[:150] + "..." if len(regional.overall_assessment) > 150 else regional.overall_assessment

        # Build inflation dict
        inflation = None
        if regional.inflation and level >= ReportLevel.STANDARD:
            inflation = regional.inflation.to_dict()

        # Build growth dict
        growth = None
        if regional.growth and level >= ReportLevel.STANDARD:
            growth = regional.growth.to_dict()

        # Build policy dict
        policy = None
        if regional.monetary_policy and level >= ReportLevel.STANDARD:
            policy = regional.monetary_policy.to_dict()

        # Limit risks/opportunities based on level
        max_items = {
            ReportLevel.EXECUTIVE: 2,
            ReportLevel.STANDARD: 3,
            ReportLevel.DEEP_DIVE: 5,
        }
        limit = max_items.get(level, 3)

        return RegionMacro(
            region=regional.region,
            headline=headline,
            inflation=inflation,
            growth=growth,
            policy=policy,
            risks=regional.key_risks[:limit],
            opportunities=regional.key_opportunities[:limit],
        )
