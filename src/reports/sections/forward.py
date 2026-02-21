"""Forward Watch section builder — regime-driven dynamic content."""

from datetime import datetime, timedelta

from src.analysis import RegimeDetector
from src.config.constants import MarketRegime
from src.reports.models import (
    ForwardSection,
    EconomicEvent,
    OutlierEvent,
    ReportLevel,
)

# Regime-specific outlier events (most relevant tail risk for each regime)
_REGIME_OUTLIERS: dict[MarketRegime, list[dict]] = {
    MarketRegime.GOLDILOCKS: [
        {
            "event": "Inflation re-acceleration forcing hawkish Fed pivot",
            "probability": "Low (10-15%)",
            "impact": "Sharp repricing of rate path, equity multiple compression, growth-to-value rotation",
            "hedge": "Short duration, long energy, reduce growth beta",
        },
        {
            "event": "Exogenous geopolitical shock breaking low-vol regime",
            "probability": "Low (10%)",
            "impact": "VIX spike to 30+, correlation spike across risk assets, safe haven bid",
            "hedge": "Long VIX calls, maintain gold allocation, reduce position sizing",
        },
    ],
    MarketRegime.INFLATIONARY_EXPANSION: [
        {
            "event": "Demand destruction tipping economy into stagflation",
            "probability": "Moderate (15-25%)",
            "impact": "Earnings downgrades, credit spread widening, cyclical underperformance",
            "hedge": "Reduce cyclical exposure, add defensive quality, extend some duration",
        },
        {
            "event": "Central bank policy error — overtightening into slowdown",
            "probability": "Moderate (15-20%)",
            "impact": "Rapid growth deceleration, curve steepening, risk-off across equities",
            "hedge": "Long 2Y treasuries, short financials, long gold",
        },
    ],
    MarketRegime.STAGFLATION: [
        {
            "event": "Recession confirmation with persistent inflation",
            "probability": "Moderate (20-30%)",
            "impact": "Equities down 15-20%, credit blowout, only gold and TIPS hold value",
            "hedge": "Overweight TIPS, gold, and cash. Underweight equity and credit",
        },
        {
            "event": "Emergency policy pivot — coordinated global easing",
            "probability": "Low (10%)",
            "impact": "Sharp relief rally in risk assets, but long-term inflation expectations spike",
            "hedge": "Maintain inflation hedges even as you add risk-on exposure on pivot",
        },
    ],
    MarketRegime.DEFLATIONARY: [
        {
            "event": "Credit event in leveraged sector triggering contagion",
            "probability": "Moderate (15-20%)",
            "impact": "Credit spread blowout, equity selloff 10-15%, flight to sovereign quality",
            "hedge": "Long duration treasuries, CDS protection on HY, reduce EM exposure",
        },
        {
            "event": "Policy response — fiscal stimulus package shifts growth expectations",
            "probability": "Moderate (15-20%)",
            "impact": "Curve steepening, value rotation, cyclical outperformance",
            "hedge": "Maintain barbell — long duration core + cyclical equity exposure",
        },
    ],
    MarketRegime.RISK_OFF: [
        {
            "event": "Systemic credit event — major bank or sovereign stress",
            "probability": "Low (5-10%)",
            "impact": "Correlation spikes to 1.0, liquidity withdrawal, all risk assets decline",
            "hedge": "Maximize cash, long treasuries, long VIX, cut all credit exposure",
        },
        {
            "event": "Capitulation selling creates generational entry point",
            "probability": "Moderate (20-30%)",
            "impact": "Sharp V-shaped recovery once forced selling exhausts — 10%+ bounce in days",
            "hedge": "Staged buying plan at predetermined levels, inverse VIX for tactical entry",
        },
    ],
    MarketRegime.RISK_ON: [
        {
            "event": "Speculative blow-off top and reversal",
            "probability": "Moderate (15-25%)",
            "impact": "VIX doubles in days, crowded positions unwind violently, meme assets collapse first",
            "hedge": "Trail stops, buy tail hedges (cheap in low-vol), reduce position sizing",
        },
        {
            "event": "Fundamental deterioration masked by momentum",
            "probability": "Moderate (15-20%)",
            "impact": "Earnings miss cycle begins, multiple compression accelerates as growth disappoints",
            "hedge": "Rotate toward quality/profitability factors, reduce pure-momentum exposure",
        },
    ],
}

# Regime-specific lessons
_REGIME_LESSONS: dict[MarketRegime, list[str]] = {
    MarketRegime.GOLDILOCKS: [
        "Goldilocks regimes reward staying invested but punish complacency. The biggest risk is assuming conditions persist forever — use low-vol environments to buy cheap protection.",
        "When everything works, the temptation is to increase leverage. History shows that peak positioning confidence precedes the sharpest drawdowns.",
    ],
    MarketRegime.INFLATIONARY_EXPANSION: [
        "Inflation regimes are deceptive — nominal returns look strong but real returns erode. Focus on assets with pricing power and real asset backing.",
        "In inflationary expansions, the Fed is your adversary. Every strong data point brings tighter policy closer. Position for the destination, not the journey.",
    ],
    MarketRegime.STAGFLATION: [
        "Stagflation is the hardest regime to navigate — traditional 60/40 fails because bonds and equities both suffer. Real assets and cash are the only reliable shelters.",
        "In stagflation, capital preservation outweighs capital appreciation. The winner is whoever loses least.",
    ],
    MarketRegime.DEFLATIONARY: [
        "Deflationary regimes reward patience and quality. Long duration assets outperform, but the journey is volatile — size positions for the drawdown, not the destination.",
        "When deflation threatens, policy response becomes the dominant variable. Position for the policy reaction, not the deflationary impulse itself.",
    ],
    MarketRegime.RISK_OFF: [
        "Risk-off regimes test conviction. Forced selling creates opportunity, but catching falling knives requires staged entry and strict risk limits.",
        "In a liquidation event, correlation goes to 1 and diversification fails. The only true hedge is cash or explicit optionality.",
    ],
    MarketRegime.RISK_ON: [
        "Risk-on regimes feel easy, which is the danger. The time to buy insurance is when premiums are cheapest — which is now.",
        "Momentum works until it doesn't. The transition from risk-on to risk-off is non-linear — it happens in days, not weeks.",
    ],
}

# Economic events with regime-specific relevance scoring
_EVENTS = [
    {"event": "FOMC Rate Decision", "importance": "high", "regimes": "all"},
    {"event": "US CPI Release", "importance": "high", "regimes": "all"},
    {"event": "US NFP Employment", "importance": "high", "regimes": "all"},
    {"event": "ECB Rate Decision", "importance": "high", "regimes": "all"},
    {"event": "US Retail Sales", "importance": "medium", "regimes": "all"},
    {"event": "US PMI Flash (Mfg/Svc)", "importance": "medium", "regimes": "all"},
    {"event": "BoJ Rate Decision", "importance": "medium", "regimes": "all"},
    {"event": "US Jobless Claims", "importance": "medium", "regimes": "all"},
    {"event": "US PCE Price Index", "importance": "high", "regimes": "all"},
    {"event": "China PMI", "importance": "medium", "regimes": "all"},
]

# Regime-specific expected impacts for key events
_EVENT_IMPACTS: dict[str, dict[MarketRegime, str]] = {
    "FOMC Rate Decision": {
        MarketRegime.GOLDILOCKS: "Fed likely on hold; dovish tilt would extend rally, hawkish surprise caps upside",
        MarketRegime.INFLATIONARY_EXPANSION: "Market expects hawkish hold; any hint of additional hikes would pressure duration",
        MarketRegime.STAGFLATION: "Policy dilemma — cut would stoke inflation, hold risks recession. Dovish pivot is the base case",
        MarketRegime.DEFLATIONARY: "Easing cycle likely; pace of cuts is the key variable for risk assets",
        MarketRegime.RISK_OFF: "Emergency response watch — any inter-meeting action signals systemic concern",
        MarketRegime.RISK_ON: "Staying accommodative fuels rally, any pushback on financial conditions risks repricing",
    },
    "US CPI Release": {
        MarketRegime.GOLDILOCKS: "Confirmation of disinflation trend extends goldilocks; upside surprise threatens regime",
        MarketRegime.INFLATIONARY_EXPANSION: "Upside surprise reinforces tightening cycle; downside opens door to policy pivot",
        MarketRegime.STAGFLATION: "Sticky inflation + weak growth is the nightmare scenario; any softening provides relief",
        MarketRegime.DEFLATIONARY: "Further deceleration confirms deflationary trend; rebound could signal false alarm",
        MarketRegime.RISK_OFF: "Hot print intensifies selling; soft print provides catalyst for recovery",
        MarketRegime.RISK_ON: "In-line print maintains status quo; upside surprise would test conviction",
    },
}


class ForwardSectionBuilder:
    """Builder for the Forward Watch section — regime-driven."""

    def __init__(self) -> None:
        self.regime_detector = RegimeDetector()

    async def build(self, level: ReportLevel) -> ForwardSection:
        regime_result = await self.regime_detector.detect_regime()
        regime = regime_result.regime

        lesson = self._generate_lesson(regime)
        events = self._get_upcoming_events(level, regime)
        outlier = self._select_outlier_event(level, regime)

        suggestions = None
        if level == ReportLevel.DEEP_DIVE:
            suggestions = self._get_positioning_suggestions(regime)

        return ForwardSection(
            lesson_of_the_day=lesson,
            upcoming_events=events,
            outlier_event=outlier,
            positioning_suggestions=suggestions,
        )

    def _generate_lesson(self, regime: MarketRegime) -> str:
        """Generate a lesson tied to the current regime."""
        import random
        lessons = _REGIME_LESSONS.get(regime, _REGIME_LESSONS[MarketRegime.GOLDILOCKS])
        return random.choice(lessons)

    def _get_upcoming_events(self, level: ReportLevel, regime: MarketRegime) -> list[EconomicEvent]:
        max_events = {ReportLevel.EXECUTIVE: 3, ReportLevel.STANDARD: 5, ReportLevel.DEEP_DIVE: 8}
        limit = max_events.get(level, 5)

        events = _EVENTS
        if level == ReportLevel.EXECUTIVE:
            events = [e for e in events if e["importance"] == "high"]

        result = []
        base_date = datetime.now()
        for i, event in enumerate(events[:limit]):
            event_date = base_date + timedelta(days=i + 1)

            # Use regime-specific impact if available, otherwise generic
            impact_map = _EVENT_IMPACTS.get(event["event"], {})
            impact = impact_map.get(regime, f"Key data release — monitor for {regime.value.replace('_', ' ')} regime confirmation or shift")

            result.append(EconomicEvent(
                date=event_date.strftime("%Y-%m-%d"),
                event=event["event"],
                importance=event["importance"],
                expected_impact=impact,
            ))

        return result

    def _select_outlier_event(self, level: ReportLevel, regime: MarketRegime) -> OutlierEvent:
        """Select the most relevant outlier for the current regime."""
        import random
        outliers = _REGIME_OUTLIERS.get(regime, _REGIME_OUTLIERS[MarketRegime.GOLDILOCKS])
        event = random.choice(outliers)

        return OutlierEvent(
            event=event["event"],
            probability=event["probability"],
            potential_impact=event["impact"],
            hedging_idea=event["hedge"] if level >= ReportLevel.STANDARD else None,
        )

    def _get_positioning_suggestions(self, regime: MarketRegime) -> list[str]:
        """Regime-specific positioning suggestions for deep dive reports."""
        suggestions: dict[MarketRegime, list[str]] = {
            MarketRegime.GOLDILOCKS: [
                "Maintain equity overweight — regime supports risk assets, but trim on strength above all-time highs",
                "Keep duration moderate — no urgency to extend but curve normalization trade has merit",
                "Use low volatility to buy tail hedges cheaply (VIX puts, SPX put spreads 3-6 months out)",
                "Favor quality growth over deep value — the macro backdrop supports earnings compounders",
            ],
            MarketRegime.INFLATIONARY_EXPANSION: [
                "Overweight commodities and energy — direct inflation beneficiaries with pricing power",
                "Keep duration short — real yields rising, long bonds face headwinds",
                "Favor value over growth — multiple compression hits high-duration equities hardest",
                "Add TIPS exposure — breakevens may still understate sticky inflation risk",
            ],
            MarketRegime.STAGFLATION: [
                "Raise cash allocation to 15-25% — optionality has value when all assets are challenged",
                "Overweight gold and TIPS — the only reliable performers in stagflation",
                "Underweight equities, especially cyclicals — earnings downgrades are coming",
                "Avoid credit risk — HY spreads have further to widen",
            ],
            MarketRegime.DEFLATIONARY: [
                "Extend duration aggressively — long-end treasuries outperform in deflation",
                "Overweight quality — strong balance sheets and cash flow visibility matter most",
                "Reduce commodity exposure — demand weakness pressures prices",
                "Watch for policy response as trigger for regime shift — have a playbook ready",
            ],
            MarketRegime.RISK_OFF: [
                "Prioritize capital preservation — raise cash, cut leverage, reduce position sizes",
                "Maintain core Treasury allocation as ballast — quality duration is the best hedge",
                "Build a staged re-entry plan at predetermined levels — don't try to time the bottom",
                "Avoid hero trades — wait for vol to normalize before rebuilding risk exposure",
            ],
            MarketRegime.RISK_ON: [
                "Participate in momentum but with trailing stops — don't let winners become losers",
                "Buy tail protection while it's cheap — VIX below 15 makes hedges attractive",
                "Favor higher-beta within equities — small caps and EM tend to outperform in risk-on",
                "Monitor positioning data for crowding — consensus trades unwind hardest",
            ],
        }
        return suggestions.get(regime, suggestions[MarketRegime.GOLDILOCKS])
