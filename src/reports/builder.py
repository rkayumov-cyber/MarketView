"""Report builder - orchestrates report generation."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from src.reports.models import (
    Report,
    ReportConfig,
    ReportLevel,
    ResearchInsight,
    ResearchInsightsSection,
)
from src.reports.sections import (
    PulseSectionBuilder,
    SentimentSectionBuilder,
    MacroSectionBuilder,
    AssetSectionBuilder,
    TechnicalsSectionBuilder,
    ForwardSectionBuilder,
)

logger = logging.getLogger(__name__)


class ReportBuilder:
    """Orchestrates the building of complete reports."""

    def __init__(self) -> None:
        self.pulse_builder = PulseSectionBuilder()
        self.sentiment_builder = SentimentSectionBuilder()
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

        # Build all sections concurrently
        tasks: list[asyncio.Task] = []
        task_names: list[str] = []

        # Core sections (always present)
        for name, builder in [
            ("pulse", self.pulse_builder),
            ("macro", self.macro_builder),
            ("assets", self.asset_builder),
            ("forward", self.forward_builder),
        ]:
            tasks.append(builder.build(level))
            task_names.append(name)

        # Optional sections — gather alongside core for max parallelism
        if config.include_sentiment:
            tasks.append(self.sentiment_builder.build(level))
            task_names.append("sentiment")

        if config.include_technicals:
            tasks.append(self.technicals_builder.build(level))
            task_names.append("technicals")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Unpack results by name
        sections: dict[str, object] = {}
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                if name in ("pulse", "macro", "assets", "forward"):
                    raise RuntimeError(f"Failed to build {name} section: {result}")
                logger.warning("Failed to build %s section: %s", name, result)
                sections[name] = None
            else:
                sections[name] = result

        pulse = sections["pulse"]
        macro = sections["macro"]
        assets = sections["assets"]
        forward = sections["forward"]
        sentiment = sections.get("sentiment")
        technicals = sections.get("technicals")

        # Research retrieval (if enabled)
        research_context: dict[str, list] = {}
        research_section = None
        if config.include_research:
            try:
                from src.reports.research_context import ResearchRetriever

                retriever = ResearchRetriever(document_ids=config.document_ids)
                research_context = retriever.retrieve_for_sections()

                # Build ResearchInsightsSection from all chunks
                all_insights: list[ResearchInsight] = []
                seen_doc_ids: set[str] = set()
                for section_name, chunks in research_context.items():
                    for chunk in chunks:
                        seen_doc_ids.add(chunk.document_id)
                        all_insights.append(
                            ResearchInsight(
                                text=chunk.text,
                                source=chunk.source,
                                document_id=chunk.document_id,
                                page=chunk.page,
                                relevance_score=chunk.score,
                                section=section_name,
                            )
                        )
                if all_insights:
                    research_section = ResearchInsightsSection(
                        insights=all_insights,
                        document_count=len(seen_doc_ids),
                        total_chunks_searched=retriever.total_chunks_searched,
                    )
            except Exception as e:
                logger.warning("Research retrieval failed, continuing without: %s", e)

        # LLM enhancement (if provider configured)
        if config.llm_provider:
            try:
                from src.llm.client import LLMClient
                from src.llm.enhancer import SectionEnhancer

                llm = LLMClient(
                    provider=config.llm_provider,
                    model=config.llm_model,
                )
                enhancer = SectionEnhancer(llm)
                _cp = config.custom_prompt
                enhance_tasks = [
                    enhancer.enhance_pulse(
                        pulse,
                        research_context=research_context.get("pulse"),
                        custom_prompt=_cp,
                    ),
                    enhancer.enhance_macro(
                        macro,
                        research_context=research_context.get("macro"),
                        custom_prompt=_cp,
                    ),
                    enhancer.enhance_forward(
                        forward,
                        research_context=research_context.get("forward"),
                        custom_prompt=_cp,
                    ),
                ]
                if sentiment:
                    enhance_tasks.append(
                        enhancer.enhance_sentiment(
                            sentiment,
                            research_context=research_context.get("sentiment"),
                            custom_prompt=_cp,
                        )
                    )
                enhanced = await asyncio.gather(
                    *enhance_tasks, return_exceptions=True
                )
                if not isinstance(enhanced[0], Exception):
                    pulse = enhanced[0]
                if not isinstance(enhanced[1], Exception):
                    macro = enhanced[1]
                if not isinstance(enhanced[2], Exception):
                    forward = enhanced[2]
                if sentiment and len(enhanced) > 3 and not isinstance(enhanced[3], Exception):
                    sentiment = enhanced[3]
            except Exception as e:
                logger.warning("LLM enhancement failed, using rule-based: %s", e)

        # Generate title
        title = config.title or self._generate_title(level, pulse)

        # Generate executive summary
        executive_summary = self._generate_executive_summary(pulse, macro, assets)

        # LLM-enhance executive summary if provider configured
        if config.llm_provider:
            try:
                from src.llm.client import LLMClient
                from src.llm.enhancer import SectionEnhancer

                llm = LLMClient(
                    provider=config.llm_provider,
                    model=config.llm_model,
                )
                enhancer = SectionEnhancer(llm)
                section_headlines = [pulse.regime.description]
                if macro.us:
                    section_headlines.append(macro.us.headline)
                if assets.equities:
                    section_headlines.append(assets.equities.headline)
                executive_summary = await enhancer.enhance_executive_summary(
                    rule_based_summary=executive_summary,
                    regime=pulse.regime.regime.replace("_", " ").title(),
                    top_asset_move=self._get_top_asset_move(assets),
                    macro_outlook=macro.global_outlook,
                    section_headlines=section_headlines,
                )
            except Exception as e:
                logger.warning("LLM exec summary enhancement failed: %s", e)

        metadata: dict = {
            "generated_at": datetime.now(UTC).isoformat(),
            "version": "1.0",
        }
        if config.llm_provider:
            metadata["llm_provider"] = config.llm_provider
            metadata["llm_model"] = config.llm_model
        if config.include_research:
            metadata["include_research"] = True

        return Report(
            report_id=report_id,
            title=title,
            level=level,
            executive_summary=executive_summary,
            config=config,
            pulse=pulse,
            sentiment=sentiment,
            macro=macro,
            assets=assets,
            technicals=technicals,
            forward=forward,
            research=research_section,
            metadata=metadata,
        )

    def _generate_executive_summary(self, pulse, macro, assets) -> str:
        """Generate a rule-based executive summary from key sections."""
        regime = pulse.regime.regime.replace("_", " ").title()
        regime_desc = pulse.regime.description

        top_move = self._get_top_asset_move(assets)
        macro_outlook = macro.global_outlook

        # 2-3 sentence summary combining regime + top move + macro
        parts = [f"Markets are in a {regime.lower()} regime. {regime_desc}"]
        if top_move:
            parts.append(top_move)
        # Add a short macro sentence (first sentence of outlook)
        first_sentence = macro_outlook.split(". ")[0].rstrip(".")
        if first_sentence:
            parts.append(f"{first_sentence}.")

        return " ".join(parts)

    @staticmethod
    def _get_top_asset_move(assets) -> str:
        """Extract the most notable asset move for the summary."""
        if assets.equities and assets.equities.us_indices:
            for name, data in assets.equities.us_indices.items():
                if isinstance(data, dict) and "change_percent" in data:
                    change = data["change_percent"]
                    price = data.get("current_price", 0)
                    return (
                        f"{name.upper()} is at {price:,.0f} "
                        f"({change:+.2f}% on the day)."
                    )
        return ""

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
            include_sentiment=False,
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
