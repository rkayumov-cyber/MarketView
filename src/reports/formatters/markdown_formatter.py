"""Markdown report formatter."""

from datetime import UTC, datetime

from src.reports.models import Report, ReportLevel


class MarkdownFormatter:
    """Formats reports as Markdown."""

    def format(self, report: Report) -> str:
        """Format report as Markdown."""
        sections = [
            self._format_header(report),
            self._format_pulse(report),
            self._format_macro(report),
            self._format_assets(report),
        ]

        if report.technicals:
            sections.append(self._format_technicals(report))

        sections.append(self._format_forward(report))
        sections.append(self._format_footer(report))

        return "\n\n".join(sections)

    def _format_header(self, report: Report) -> str:
        """Format report header."""
        lines = [
            f"# {report.title}",
            "",
            f"**Report ID:** {report.report_id}",
            f"**Generated:** {report.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Level:** {report.level.name}",
            "",
            "---",
        ]
        return "\n".join(lines)

    def _format_pulse(self, report: Report) -> str:
        """Format The Pulse section."""
        pulse = report.pulse
        lines = [
            "## I. THE PULSE",
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

        # Sentiment
        if pulse.sentiment and report.level >= ReportLevel.STANDARD:
            lines.extend([
                "### Sentiment Analysis",
                f"- Overall Sentiment Score: {pulse.sentiment.overall_score:.2f}",
                f"- Bullish Ratio: {pulse.sentiment.bullish_ratio:.0%}",
            ])

            if pulse.sentiment.trending_tickers:
                tickers = [f"${t[0]}" for t in pulse.sentiment.trending_tickers[:5]]
                lines.append(f"- Trending: {', '.join(tickers)}")
            lines.append("")

        # Divergences
        if pulse.divergences:
            lines.append("### ⚠️ Divergences")
            for div in pulse.divergences:
                lines.extend([
                    f"**{div.description}**",
                    f"- Data Signal: {div.data_signal}",
                    f"- Sentiment Signal: {div.sentiment_signal}",
                    "",
                ])

        # Big Narrative
        lines.extend([
            "### The Big Narrative",
            pulse.big_narrative,
            "",
        ])

        # Key Takeaways
        lines.append("### Key Takeaways")
        for takeaway in pulse.key_takeaways:
            lines.append(f"- {takeaway}")

        return "\n".join(lines)

    def _format_macro(self, report: Report) -> str:
        """Format Macro Analysis section."""
        macro = report.macro
        lines = [
            "## II. MACRO ANALYSIS",
            "",
        ]

        # US
        if macro.us:
            lines.extend([
                "### 🇺🇸 United States",
                macro.us.headline,
                "",
            ])

            if macro.us.inflation and report.level >= ReportLevel.STANDARD:
                lines.append(f"**Inflation:** {macro.us.inflation.get('assessment', 'N/A')}")

            if macro.us.growth and report.level >= ReportLevel.STANDARD:
                lines.append(f"**Growth:** {macro.us.growth.get('assessment', 'N/A')}")

            if macro.us.policy and report.level >= ReportLevel.STANDARD:
                lines.append(f"**Policy:** {macro.us.policy.get('assessment', 'N/A')}")

            if macro.us.risks:
                lines.append("\n**Risks:**")
                for risk in macro.us.risks:
                    lines.append(f"- {risk}")

            if macro.us.opportunities:
                lines.append("\n**Opportunities:**")
                for opp in macro.us.opportunities:
                    lines.append(f"- {opp}")

            lines.append("")

        # EU
        if macro.eu:
            lines.extend([
                "### 🇪🇺 Europe",
                macro.eu.headline,
                "",
            ])

            if macro.eu.risks:
                lines.append("**Risks:**")
                for risk in macro.eu.risks:
                    lines.append(f"- {risk}")
            lines.append("")

        # Asia
        if macro.asia:
            lines.extend([
                "### 🌏 Asia",
                macro.asia.headline,
                "",
            ])

            if macro.asia.risks:
                lines.append("**Risks:**")
                for risk in macro.asia.risks:
                    lines.append(f"- {risk}")
            lines.append("")

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

    def _format_assets(self, report: Report) -> str:
        """Format Asset Class section."""
        assets = report.assets
        lines = [
            "## III. ASSET CLASS DEEP DIVE",
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

    def _format_technicals(self, report: Report) -> str:
        """Format Technicals section."""
        if not report.technicals:
            return ""

        tech = report.technicals
        lines = [
            "## IV. TECHNICALS & POSITIONING",
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

    def _format_forward(self, report: Report) -> str:
        """Format Forward Watch section."""
        forward = report.forward
        lines = [
            "## V. THE FORWARD WATCH",
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

    def _format_footer(self, report: Report) -> str:
        """Format report footer."""
        lines = [
            "---",
            "",
            "*This report is generated automatically by MarketView and is for informational purposes only. "
            "It does not constitute investment advice.*",
            "",
            f"*Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        ]
        return "\n".join(lines)
