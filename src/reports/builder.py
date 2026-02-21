"""Report builder - orchestrates report generation."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from src.config.constants import MarketRegime
from src.reports.models import (
    PositioningSummaryItem,
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

        # Generate thesis — connects regime → macro → assets → positioning
        thesis = self._generate_thesis(pulse, macro, assets, sentiment)

        # Generate positioning summary
        positioning_summary = self._generate_positioning_summary(pulse, macro, assets)

        return Report(
            report_id=report_id,
            title=title,
            level=level,
            executive_summary=executive_summary,
            thesis=thesis,
            positioning_summary=positioning_summary,
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
        """Generate an analytical executive summary — not just data, but meaning."""
        regime = pulse.regime.regime.replace("_", " ")
        confidence = pulse.regime.confidence

        # Lead with the regime and confidence
        if confidence > 0.6:
            conviction = "with high conviction"
        elif confidence > 0.4:
            conviction = "with moderate conviction"
        else:
            conviction = "though signals are mixed"

        parts = [f"Markets are in a **{regime}** regime {conviction} ({confidence:.0%})."]

        # Add the most meaningful asset move with context
        top_move = self._get_top_asset_move(assets)
        if top_move:
            parts.append(top_move)

        # Macro connection
        if macro.us and macro.us.headline:
            first = macro.us.headline.split(".")[0].rstrip(".")
            parts.append(f"{first}.")

        # Sentiment overlay if available
        if pulse.sentiment:
            if pulse.divergences:
                parts.append(
                    f"Notable divergence: {pulse.divergences[0].description.lower()}."
                )
            else:
                bull = pulse.sentiment.bullish_ratio
                if bull > 0.65:
                    parts.append("Retail sentiment skews heavily bullish — watch for positioning crowding.")
                elif bull < 0.35:
                    parts.append("Retail sentiment is bearish — contrarian buyers may find opportunity.")

        return " ".join(parts)

    def _generate_thesis(self, pulse, macro, assets, sentiment) -> str:
        """Generate a connecting thesis: regime → macro → assets → what to do."""
        regime = pulse.regime.regime.replace("_", " ")
        regime_enum = MarketRegime(pulse.regime.regime)

        # Import implications
        from src.analysis import RegimeDetector
        impl = RegimeDetector().get_regime_implications(regime_enum)

        parts = []

        # 1. Regime + macro linkage
        eq_bias = impl.get("equities", {}).get("bias", "neutral")
        fi_bias = impl.get("fixed_income", {}).get("bias", "neutral")
        comm_bias = impl.get("commodities", {}).get("bias", "neutral")

        parts.append(
            f"The dominant theme is **{regime}**. "
            f"This regime historically favors {eq_bias} equity positioning, "
            f"{fi_bias} fixed income, and {comm_bias} commodities."
        )

        # 2. Macro confirmation or contradiction
        if macro.us and macro.us.inflation:
            inf = macro.us.inflation
            if isinstance(inf, dict):
                inf_trend = inf.get("trend", "stable")
            else:
                inf_trend = inf.trend if hasattr(inf, "trend") else "stable"

            if regime_enum in (MarketRegime.GOLDILOCKS, MarketRegime.RISK_ON) and inf_trend == "rising":
                parts.append(
                    "However, rising inflation poses a risk to regime persistence — "
                    "monitor closely for regime transition signals."
                )
            elif regime_enum == MarketRegime.STAGFLATION and inf_trend == "falling":
                parts.append(
                    "Encouraging sign: inflation trend is turning lower, which could "
                    "catalyze a regime shift toward goldilocks if growth stabilizes."
                )
            else:
                parts.append(f"Macro data confirms the regime — inflation trend is {inf_trend}.")

        # 3. Asset class alignment check
        if assets.equities and assets.equities.vix:
            vix_level = assets.equities.vix.get("current_price", 0)
            if regime_enum == MarketRegime.GOLDILOCKS and vix_level > 20:
                parts.append(
                    f"VIX at {vix_level:.1f} is inconsistent with goldilocks — "
                    "this disconnect often resolves with either a vol mean-reversion or regime shift."
                )
            elif regime_enum == MarketRegime.RISK_OFF and vix_level < 20:
                parts.append(
                    f"VIX at {vix_level:.1f} appears low for a risk-off environment — "
                    "either stress is contained or markets are underpricing tail risk."
                )

        # 4. Actionable conclusion
        sectors = impl.get("equities", {}).get("sectors", [])
        if sectors:
            sector_list = ", ".join(s.replace("_", " ") for s in sectors[:3])
            parts.append(f"Favored sectors: {sector_list}.")

        return " ".join(parts)

    def _generate_positioning_summary(self, pulse, macro, assets) -> list[PositioningSummaryItem]:
        """Generate a positioning summary table based on regime implications."""
        regime_enum = MarketRegime(pulse.regime.regime)
        from src.analysis import RegimeDetector
        impl = RegimeDetector().get_regime_implications(regime_enum)
        confidence = pulse.regime.confidence

        # Map bias strings to positioning labels
        bias_map = {
            "bullish": "Overweight",
            "bearish": "Underweight",
            "cautious": "Underweight",
            "neutral": "Neutral",
            "mixed": "Neutral",
        }

        conviction = "High" if confidence > 0.6 else ("Medium" if confidence > 0.4 else "Low")

        items = []

        # Equities
        eq_impl = impl.get("equities", {})
        eq_bias = eq_impl.get("bias", "neutral")
        eq_sectors = eq_impl.get("sectors", [])
        items.append(PositioningSummaryItem(
            asset_class="Equities",
            bias=bias_map.get(eq_bias, "Neutral"),
            conviction=conviction,
            rationale=f"{regime_enum.value.replace('_', ' ').title()} regime favors "
                      f"{', '.join(s.replace('_', ' ') for s in eq_sectors[:2]) if eq_sectors else 'balanced allocation'}",
        ))

        # Fixed Income
        fi_impl = impl.get("fixed_income", {})
        fi_bias = fi_impl.get("bias", "neutral")
        duration = fi_impl.get("duration", "moderate")
        items.append(PositioningSummaryItem(
            asset_class="Fixed Income",
            bias=bias_map.get(fi_bias, "Neutral"),
            conviction=conviction,
            rationale=f"Duration: {duration}. "
                      + ("Quality over credit." if fi_bias == "bullish" else "Favor carry where spreads compensate."),
        ))

        # Commodities
        comm_impl = impl.get("commodities", {})
        comm_bias = comm_impl.get("bias", "neutral")
        focus = comm_impl.get("focus", [])
        items.append(PositioningSummaryItem(
            asset_class="Commodities",
            bias=bias_map.get(comm_bias, "Neutral"),
            conviction="Medium",
            rationale=f"Focus on {', '.join(focus)}" if focus else "Broad commodity exposure appropriate",
        ))

        # Crypto
        crypto_impl = impl.get("crypto", {})
        crypto_bias = crypto_impl.get("bias", "neutral")
        items.append(PositioningSummaryItem(
            asset_class="Crypto",
            bias=bias_map.get(crypto_bias, "Neutral"),
            conviction="Low",
            rationale="High-beta play on risk sentiment — position size accordingly",
        ))

        # FX
        fx_impl = impl.get("fx", {})
        fx_bias = fx_impl.get("bias", "neutral")
        fx_label = {"usd_bullish": "Overweight USD", "safe_haven": "Overweight USD/JPY/CHF",
                     "risk_currencies": "Overweight AUD/NZD/EM", "neutral": "Neutral"}.get(fx_bias, "Neutral")
        items.append(PositioningSummaryItem(
            asset_class="FX",
            bias=fx_label,
            conviction=conviction,
            rationale=f"Dollar dynamics driven by {regime_enum.value.replace('_', ' ')} regime and Fed path",
        ))

        return items

    @staticmethod
    def _get_top_asset_move(assets) -> str:
        """Extract the most notable asset move for the summary."""
        if assets.equities and assets.equities.us_indices:
            for name, data in assets.equities.us_indices.items():
                if isinstance(data, dict) and "change_percent" in data:
                    change = data["change_percent"]
                    price = data.get("current_price", 0)
                    return (
                        f"{name.upper()} at {price:,.0f} "
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
