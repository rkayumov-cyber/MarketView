"""Forward Watch section builder."""

from datetime import datetime, timedelta

from src.reports.models import (
    ForwardSection,
    EconomicEvent,
    OutlierEvent,
    ReportLevel,
)


class ForwardSectionBuilder:
    """Builder for the Forward Watch section."""

    # Static economic calendar (would be dynamic in production)
    ECONOMIC_EVENTS = [
        {"event": "FOMC Rate Decision", "importance": "high", "impact": "Sets monetary policy direction"},
        {"event": "US CPI Release", "importance": "high", "impact": "Inflation trajectory watch"},
        {"event": "US NFP Employment", "importance": "high", "impact": "Labor market health indicator"},
        {"event": "ECB Rate Decision", "importance": "high", "impact": "European policy direction"},
        {"event": "US Retail Sales", "importance": "medium", "impact": "Consumer spending gauge"},
        {"event": "US PMI Flash", "importance": "medium", "impact": "Manufacturing/services activity"},
        {"event": "BOJ Rate Decision", "importance": "medium", "impact": "Yen volatility catalyst"},
        {"event": "US Jobless Claims", "importance": "medium", "impact": "Weekly labor market pulse"},
    ]

    OUTLIER_EVENTS = [
        {
            "event": "Geopolitical escalation in Middle East",
            "probability": "Low (10-15%)",
            "impact": "Oil spike to $100+, risk-off across assets, safe haven bid",
            "hedge": "Long oil, long gold, short EM equities",
        },
        {
            "event": "Fed emergency rate cut",
            "probability": "Very low (5%)",
            "impact": "Sharp rally in risk assets, dollar weakness, curve steepening",
            "hedge": "Long duration, short dollar",
        },
        {
            "event": "Major bank credit event",
            "probability": "Low (10%)",
            "impact": "Credit spread blowout, equity selloff, flight to quality",
            "hedge": "Long CDS protection, long treasuries",
        },
        {
            "event": "China Taiwan tensions escalation",
            "probability": "Low (5-10%)",
            "impact": "Risk-off, semiconductor supply shock, safe haven bid",
            "hedge": "Reduce Taiwan/China exposure, long volatility",
        },
    ]

    async def build(self, level: ReportLevel) -> ForwardSection:
        """Build the Forward Watch section."""
        # Generate lesson of the day
        lesson = self._generate_lesson()

        # Get upcoming events
        events = self._get_upcoming_events(level)

        # Select outlier event
        outlier = self._select_outlier_event(level)

        # Positioning suggestions for deep dive
        suggestions = None
        if level == ReportLevel.DEEP_DIVE:
            suggestions = self._get_positioning_suggestions()

        return ForwardSection(
            lesson_of_the_day=lesson,
            upcoming_events=events,
            outlier_event=outlier,
            positioning_suggestions=suggestions,
        )

    def _generate_lesson(self) -> str:
        """Generate lesson of the day based on recent market action."""
        # In production, this would analyze recent price action
        lessons = [
            "Markets can stay irrational longer than you can stay solvent. Position sizing matters.",
            "The trend is your friend until it ends. Respect momentum but watch for divergences.",
            "Correlation goes to 1 in a crisis. Diversification works until you need it most.",
            "Central bank policy remains the dominant macro driver. Don't fight the Fed.",
            "Sentiment extremes often mark turning points. Be contrarian when consensus is strong.",
        ]

        # Rotate based on day of week
        day_index = datetime.now().weekday()
        return lessons[day_index % len(lessons)]

    def _get_upcoming_events(self, level: ReportLevel) -> list[EconomicEvent]:
        """Get upcoming economic events."""
        # Number of events based on level
        max_events = {
            ReportLevel.EXECUTIVE: 3,
            ReportLevel.STANDARD: 5,
            ReportLevel.DEEP_DIVE: 8,
        }
        limit = max_events.get(level, 5)

        # Filter to high importance for executive level
        events = self.ECONOMIC_EVENTS
        if level == ReportLevel.EXECUTIVE:
            events = [e for e in events if e["importance"] == "high"]

        # Generate dates (simulated)
        result = []
        base_date = datetime.now()

        for i, event in enumerate(events[:limit]):
            event_date = base_date + timedelta(days=i + 1)
            result.append(EconomicEvent(
                date=event_date.strftime("%Y-%m-%d"),
                event=event["event"],
                importance=event["importance"],
                expected_impact=event["impact"],
            ))

        return result

    def _select_outlier_event(self, level: ReportLevel) -> OutlierEvent:
        """Select an outlier event to watch."""
        import random

        # Select based on current macro context
        # In production, this would be more intelligent
        event = random.choice(self.OUTLIER_EVENTS)

        return OutlierEvent(
            event=event["event"],
            probability=event["probability"],
            potential_impact=event["impact"],
            hedging_idea=event["hedge"] if level >= ReportLevel.STANDARD else None,
        )

    def _get_positioning_suggestions(self) -> list[str]:
        """Get positioning suggestions for deep dive reports."""
        return [
            "Consider reducing equity beta if VIX sustains below 15 - asymmetric risk/reward",
            "Dollar positioning: tactically neutral, wait for clearer Fed path",
            "Maintain some gold exposure as portfolio hedge",
            "Credit spreads tight - favor up-in-quality in HY allocation",
            "Crypto: position size appropriately given volatility - not a core holding",
        ]
