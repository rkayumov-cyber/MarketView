"""Markdown report formatter."""

from datetime import UTC, datetime

from src.reports.models import Report, ReportLevel

_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


class _Counter:
    """Auto-incrementing Roman numeral counter for section headings."""

    def __init__(self) -> None:
        self._n = 0

    def __call__(self) -> str:
        idx = self._n
        self._n += 1
        return _ROMAN[idx] if idx < len(_ROMAN) else str(idx + 1)


class MarkdownFormatter:
    """Formats reports as Markdown."""

    def format(self, report: Report) -> str:
        """Format report as Markdown."""
        # Dynamic section numbering
        num = _Counter()

        sections = [
            self._format_header(report),
            self._format_executive_summary(report),
            self._format_thesis(report),
            self._format_positioning_summary(report),
            self._format_pulse(report, num()),
        ]

        if report.sentiment:
            sections.append(self._format_sentiment(report, num()))

        sections.append(self._format_macro(report, num()))
        sections.append(self._format_assets(report, num()))

        if report.technicals:
            sections.append(self._format_technicals(report, num()))

        sections.append(self._format_forward(report, num()))

        if report.research and report.research.insights:
            sections.append(self._format_research(report, num()))

        sections.append(self._format_footer())

        return "\n\n".join(s for s in sections if s)

    def _format_header(self, report: Report) -> str:
        """Format report header — clean title and date only."""
        date_line = report.created_at.strftime("%B %d, %Y at %H:%M UTC")
        lines = [
            f"# {report.title}",
            f"*Generated {date_line}*",
        ]
        return "\n".join(lines)

    def _format_executive_summary(self, report: Report) -> str:
        """Format executive summary as a blockquote."""
        if not report.executive_summary:
            return ""
        # Wrap each sentence-line as a blockquote
        lines = [f"> {line}" for line in report.executive_summary.split("\n") if line.strip()]
        return "\n".join(lines)

    def _format_thesis(self, report: Report) -> str:
        """Format the investment thesis — the connective narrative."""
        if not report.thesis:
            return ""
        lines = [
            "## Investment Thesis",
            "",
            report.thesis,
        ]
        return "\n".join(lines)

    def _format_positioning_summary(self, report: Report) -> str:
        """Format the positioning summary table."""
        if not report.positioning_summary:
            return ""
        lines = [
            "## Positioning Summary",
            "",
            "| Asset Class | Bias | Conviction | Rationale |",
            "|-------------|------|------------|-----------|",
        ]
        for item in report.positioning_summary:
            lines.append(
                f"| {item.asset_class} | {item.bias} | {item.conviction} | {item.rationale} |"
            )
        return "\n".join(lines)

    def _format_pulse(self, report: Report, num: str) -> str:
        """Format the Market Pulse section."""
        pulse = report.pulse
        lines = [
            f"## {num}. Market Pulse",
            "",
            f"### Market Regime: {pulse.regime.regime.replace('_', ' ').title()}",
            f"*Confidence: {pulse.regime.confidence:.0%}*",
            "",
            pulse.regime.description,
            "",
        ]

        # Signals
        if pulse.regime.signals:
            lines.append("**Key Signals:**")
            for signal in pulse.regime.signals:
                lines.append(f"- {signal}")
            lines.append("")

        # Divergences — clean callout blocks
        if pulse.divergences:
            for div in pulse.divergences:
                lines.append(
                    f"> **Divergence:** {div.description} — "
                    f"data suggests {div.data_signal.lower()} "
                    f"while sentiment points to {div.sentiment_signal.lower()}."
                )
                lines.append("")

        # Big Narrative — no subheading, just the text
        lines.append(pulse.big_narrative)
        lines.append("")

        # Key Takeaways
        lines.append("### Key Takeaways")
        for takeaway in pulse.key_takeaways:
            lines.append(f"- {takeaway}")

        return "\n".join(lines)

    def _format_sentiment(self, report: Report, num: str) -> str:
        """Format the Sentiment Analysis section."""
        sent = report.sentiment
        if not sent:
            return ""

        lines = [
            f"## {num}. Sentiment Analysis",
            "",
            f"**Overall: {sent.overall_label}** (score: {sent.overall_score:+.2f}, "
            f"{sent.bullish_ratio:.0%} bullish)",
            f"*{sent.total_posts} posts analyzed across {sent.subreddit_count} communities*",
            "",
            sent.narrative,
            "",
        ]

        # Trending tickers
        if sent.trending_tickers:
            lines.append("### Trending Tickers")
            lines.append("")
            lines.append("| Ticker | Mentions |")
            lines.append("|--------|----------|")
            for ticker, count in sent.trending_tickers[:10]:
                lines.append(f"| ${ticker} | {count} |")
            lines.append("")

        # Subreddit breakdowns (L2+)
        if sent.subreddit_breakdowns and report.level >= ReportLevel.STANDARD:
            lines.append("### Community Breakdown")
            lines.append("")
            lines.append("| Community | Score | Bullish | Posts | Top Ticker |")
            lines.append("|-----------|-------|---------|-------|------------|")
            for b in sent.subreddit_breakdowns:
                top = f"${b.top_tickers[0][0]}" if b.top_tickers else "-"
                lines.append(
                    f"| r/{b.subreddit} | {b.sentiment_score:+.2f} | "
                    f"{b.bullish_ratio:.0%} | {b.post_count} | {top} |"
                )
            lines.append("")

        # Contrarian signals
        if sent.contrarian_signals:
            lines.append("### Contrarian Signals")
            for signal in sent.contrarian_signals:
                lines.append(f"- {signal}")
            lines.append("")

        return "\n".join(lines)

    def _format_macro(self, report: Report, num: str) -> str:
        """Format Macro Overview section."""
        macro = report.macro
        lines = [
            f"## {num}. Macro Overview",
            "",
        ]

        # US
        if macro.us:
            lines.extend(self._format_region(
                "United States", macro.us, report.level,
            ))

        # EU
        if macro.eu:
            lines.extend(self._format_region(
                "Europe", macro.eu, report.level,
            ))

        # Asia
        if macro.asia:
            lines.extend(self._format_region(
                "Asia-Pacific", macro.asia, report.level,
            ))

        # Global Outlook
        lines.extend([
            "### Global Outlook",
            macro.global_outlook,
            "",
        ])

        # Themes
        if macro.themes:
            lines.append("**Cross-Regional Themes:**")
            for theme in macro.themes:
                lines.append(f"- {theme}")

        return "\n".join(lines)

    def _format_region(
        self, name: str, region, level: ReportLevel,
    ) -> list[str]:
        """Format a single macro region with consistent structure."""
        lines = [
            f"### {name}",
            region.headline,
            "",
        ]

        if region.inflation and level >= ReportLevel.STANDARD:
            lines.append(f"**Inflation:** {region.inflation.get('assessment', 'N/A')}")

        if region.growth and level >= ReportLevel.STANDARD:
            lines.append(f"**Growth:** {region.growth.get('assessment', 'N/A')}")

        if region.policy and level >= ReportLevel.STANDARD:
            lines.append(f"**Policy:** {region.policy.get('assessment', 'N/A')}")

        if region.risks:
            lines.append("\n**Risks:**")
            for risk in region.risks:
                lines.append(f"- {risk}")

        if region.opportunities:
            lines.append("\n**Opportunities:**")
            for opp in region.opportunities:
                lines.append(f"- {opp}")

        lines.append("")
        return lines

    def _format_assets(self, report: Report, num: str) -> str:
        """Format Asset Classes section."""
        assets = report.assets
        lines = [
            f"## {num}. Asset Classes",
            "",
        ]

        # Equities
        if assets.equities:
            eq = assets.equities
            lines.extend([
                "### Equities",
                f"**{eq.headline}**",
                "",
                eq.commentary,
                "",
            ])

            if eq.us_indices and report.level >= ReportLevel.STANDARD:
                lines.append("| Index | Price | Change |")
                lines.append("|-------|-------|--------|")
                for name, data in eq.us_indices.items():
                    if isinstance(data, dict):
                        price = data.get("current_price", 0)
                        change = data.get("change_percent", 0)
                        lines.append(f"| {name.upper()} | {price:,.2f} | {change:+.2f}% |")
                lines.append("")

            if eq.sectors and report.level >= ReportLevel.DEEP_DIVE:
                sorted_sectors = sorted(eq.sectors.items(), key=lambda x: x[1], reverse=True)
                lines.append("**Sector Performance:**")
                for sector, perf in sorted_sectors:
                    lines.append(f"- {sector.replace('_', ' ').title()}: {perf:+.2f}%")
                lines.append("")

        # Fixed Income
        if assets.fixed_income:
            fi = assets.fixed_income
            lines.extend([
                "### Fixed Income",
                f"**{fi.headline}**",
                "",
                fi.commentary,
                "",
            ])

            if fi.yield_curve and report.level >= ReportLevel.STANDARD:
                lines.append("| Tenor | Yield |")
                lines.append("|-------|-------|")
                for tenor, rate in fi.yield_curve.items():
                    if rate is not None:
                        lines.append(f"| {tenor.replace('_', ' ').title()} | {rate:.2f}% |")
                lines.append("")

        # FX
        if assets.fx:
            fx = assets.fx
            lines.extend([
                "### Foreign Exchange",
                f"**{fx.headline}**",
                "",
                fx.commentary,
                "",
            ])

            if fx.dm_pairs and report.level >= ReportLevel.STANDARD:
                lines.append("| Pair | Rate | Change |")
                lines.append("|------|------|--------|")
                for name, data in fx.dm_pairs.items():
                    if isinstance(data, dict):
                        rate = data.get("rate", 0)
                        change = data.get("change_percent", 0)
                        lines.append(f"| {name.upper()} | {rate:.4f} | {change:+.2f}% |")
                lines.append("")

        # Commodities
        if assets.commodities:
            comm = assets.commodities
            lines.extend([
                "### Commodities",
                f"**{comm.headline}**",
                "",
                comm.commentary,
                "",
            ])

        # Crypto
        if assets.crypto:
            crypto = assets.crypto
            lines.extend([
                "### Crypto",
                f"**{crypto.headline}**",
                "",
                crypto.commentary,
                "",
            ])

            if crypto.fear_greed and report.level >= ReportLevel.STANDARD:
                fg = crypto.fear_greed
                lines.append(f"*Fear & Greed: {fg.get('classification', 'N/A')} ({fg.get('value', 0):.0f}/100)*")
                lines.append("")

        return "\n".join(lines)

    def _format_technicals(self, report: Report, num: str) -> str:
        """Format Technicals & Positioning section."""
        if not report.technicals:
            return ""

        tech = report.technicals
        lines = [
            f"## {num}. Technicals & Positioning",
            "",
        ]

        # Key Levels
        if tech.key_levels:
            lines.extend([
                "### Major Levels",
                "",
                "| Asset | Price | S1 | S2 | R1 | R2 | RSI | Signal |",
                "|-------|-------|----|----|----|----|-----|--------|",
            ])

            for level in tech.key_levels:
                lines.append(
                    f"| {level.asset} | {level.current_price:,.2f} | "
                    f"{level.support_1:,.2f} | {level.support_2:,.2f} | "
                    f"{level.resistance_1:,.2f} | {level.resistance_2:,.2f} | "
                    f"{level.rsi:.0f} | {level.signal.title()} |"
                )
            lines.append("")

        # Volatility
        lines.extend([
            "### Volatility Analysis",
            tech.volatility.assessment,
            "",
        ])

        if tech.volatility.vix:
            lines.append(f"- VIX: {tech.volatility.vix:.2f}")
        if tech.volatility.vix_percentile:
            lines.append(f"- VIX Percentile: {tech.volatility.vix_percentile:.0f}%")
        lines.append("")

        # Positioning
        if tech.positioning:
            lines.extend([
                "### Positioning",
                f"- Retail: {tech.positioning.retail_sentiment}",
            ])
            if tech.positioning.institutional_flows:
                lines.append(f"- Institutional: {tech.positioning.institutional_flows}")
            lines.append("")

        # Correlations
        if tech.correlations:
            lines.extend([
                "### Correlation Insights",
                "",
            ])
            for corr in tech.correlations:
                lines.append(f"- **{corr.pair}** ({corr.correlation:+.2f}): {corr.interpretation}")
            lines.append("")

        return "\n".join(lines)

    def _format_forward(self, report: Report, num: str) -> str:
        """Format Forward Watch section."""
        forward = report.forward
        lines = [
            f"## {num}. Forward Watch",
            "",
            "### Lesson of the Day",
            f"*{forward.lesson_of_the_day}*",
            "",
            "### Upcoming Events",
            "",
            "| Date | Event | Importance | Expected Impact |",
            "|------|-------|------------|-----------------|",
        ]

        for event in forward.upcoming_events:
            importance_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(event.importance, "")
            lines.append(
                f"| {event.date} | {event.event} | {importance_emoji} {event.importance.title()} | "
                f"{event.expected_impact} |"
            )
        lines.append("")

        # Outlier Event
        lines.extend([
            "### The Outlier Watch",
            f"**{forward.outlier_event.event}**",
            "",
            f"- Probability: {forward.outlier_event.probability}",
            f"- Potential Impact: {forward.outlier_event.potential_impact}",
        ])

        if forward.outlier_event.hedging_idea:
            lines.append(f"- Hedging Idea: {forward.outlier_event.hedging_idea}")
        lines.append("")

        # Positioning suggestions
        if forward.positioning_suggestions:
            lines.append("### Positioning Suggestions")
            for suggestion in forward.positioning_suggestions:
                lines.append(f"- {suggestion}")

        return "\n".join(lines)

    def _format_research(self, report: Report, num: str) -> str:
        """Format the Supporting Research section."""
        research = report.research
        if not research or not research.insights:
            return ""

        lines = [
            f"## {num}. Supporting Research",
            "",
        ]

        # Group insights by section
        by_section: dict[str, list] = {}
        for insight in research.insights:
            by_section.setdefault(insight.section, []).append(insight)

        section_labels = {
            "pulse": "Market Pulse",
            "macro": "Macro Overview",
            "assets": "Asset Classes",
            "sentiment": "Sentiment",
            "forward": "Forward Watch",
        }

        for section_key, insights in by_section.items():
            label = section_labels.get(section_key, section_key.title())
            lines.append(f"### {label}")
            lines.append("")
            for ins in insights:
                # Clean excerpt — no truncation ellipsis, no scores
                excerpt = ins.text.strip()
                source_attr = f"*{ins.source}*"
                lines.append(f"> {excerpt}")
                lines.append(f"> — {source_attr}")
                lines.append("")

        return "\n".join(lines)

    def _format_footer(self) -> str:
        """Format report footer — just the disclaimer."""
        lines = [
            "---",
            "",
            "*This report is generated automatically by MarketView and is for informational purposes only. "
            "It does not constitute investment advice.*",
        ]
        return "\n".join(lines)
