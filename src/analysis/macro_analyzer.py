"""Macro economic analysis for different regions."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.config.constants import Region
from src.ingestion.tier1_core import FREDClient


@dataclass
class InflationAnalysis:
    """Inflation analysis result."""

    headline_cpi: float | None
    core_cpi: float | None
    pce: float | None
    core_pce: float | None
    breakeven_5y: float | None
    breakeven_10y: float | None
    trend: str  # "rising", "falling", "stable"
    assessment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline_cpi": self.headline_cpi,
            "core_cpi": self.core_cpi,
            "pce": self.pce,
            "core_pce": self.core_pce,
            "breakeven_5y": self.breakeven_5y,
            "breakeven_10y": self.breakeven_10y,
            "trend": self.trend,
            "assessment": self.assessment,
        }


@dataclass
class GrowthAnalysis:
    """Growth analysis result."""

    gdp_growth: float | None
    real_gdp: float | None
    trend: str
    assessment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "gdp_growth": self.gdp_growth,
            "real_gdp": self.real_gdp,
            "trend": self.trend,
            "assessment": self.assessment,
        }


@dataclass
class LaborAnalysis:
    """Labor market analysis result."""

    unemployment: float | None
    nonfarm_payrolls: float | None
    initial_claims: float | None
    trend: str
    assessment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "unemployment": self.unemployment,
            "nonfarm_payrolls": self.nonfarm_payrolls,
            "initial_claims": self.initial_claims,
            "trend": self.trend,
            "assessment": self.assessment,
        }


@dataclass
class MonetaryPolicyAnalysis:
    """Monetary policy analysis result."""

    fed_funds: float | None
    treasury_2y: float | None
    treasury_10y: float | None
    spread_2s10s: float | None
    policy_stance: str  # "hawkish", "dovish", "neutral"
    assessment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fed_funds": self.fed_funds,
            "treasury_2y": self.treasury_2y,
            "treasury_10y": self.treasury_10y,
            "spread_2s10s": self.spread_2s10s,
            "policy_stance": self.policy_stance,
            "assessment": self.assessment,
        }


@dataclass
class RegionalAnalysis:
    """Regional macro analysis result."""

    region: str
    inflation: InflationAnalysis | None
    growth: GrowthAnalysis | None
    labor: LaborAnalysis | None
    monetary_policy: MonetaryPolicyAnalysis | None
    overall_assessment: str
    key_risks: list[str]
    key_opportunities: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "region": self.region,
            "inflation": self.inflation.to_dict() if self.inflation else None,
            "growth": self.growth.to_dict() if self.growth else None,
            "labor": self.labor.to_dict() if self.labor else None,
            "monetary_policy": self.monetary_policy.to_dict() if self.monetary_policy else None,
            "overall_assessment": self.overall_assessment,
            "key_risks": self.key_risks,
            "key_opportunities": self.key_opportunities,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MacroAnalysis:
    """Complete macro analysis across regions."""

    us: RegionalAnalysis | None
    eu: RegionalAnalysis | None
    asia: RegionalAnalysis | None
    global_outlook: str
    cross_regional_themes: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "us": self.us.to_dict() if self.us else None,
            "eu": self.eu.to_dict() if self.eu else None,
            "asia": self.asia.to_dict() if self.asia else None,
            "global_outlook": self.global_outlook,
            "cross_regional_themes": self.cross_regional_themes,
            "timestamp": self.timestamp.isoformat(),
        }


class MacroAnalyzer:
    """Macro economic analyzer."""

    def __init__(self) -> None:
        self.fred = FREDClient()

    async def analyze_us(self) -> RegionalAnalysis:
        """Analyze US macro conditions."""
        # Fetch all US data
        inflation_data = await self.fred.get_inflation_data()
        growth_data = await self.fred.get_growth_data()
        labor_data = await self.fred.get_labor_data()
        rates_data = await self.fred.get_rates_data()
        yield_curve = await self.fred.get_yield_curve()

        # Analyze inflation
        inflation = self._analyze_us_inflation(inflation_data)

        # Analyze growth
        growth = self._analyze_us_growth(growth_data)

        # Analyze labor
        labor = self._analyze_us_labor(labor_data)

        # Analyze monetary policy
        monetary = self._analyze_us_monetary(rates_data, yield_curve)

        # Generate overall assessment
        overall, risks, opportunities = self._generate_us_assessment(
            inflation, growth, labor, monetary
        )

        return RegionalAnalysis(
            region="US",
            inflation=inflation,
            growth=growth,
            labor=labor,
            monetary_policy=monetary,
            overall_assessment=overall,
            key_risks=risks,
            key_opportunities=opportunities,
        )

    def _analyze_us_inflation(self, data: dict) -> InflationAnalysis:
        """Analyze US inflation data."""
        cpi = data.get("cpi")
        core_cpi = data.get("core_cpi")
        pce = data.get("pce")
        core_pce = data.get("core_pce")
        be_5y = data.get("breakeven_5y")
        be_10y = data.get("breakeven_10y")

        # Get values
        cpi_val = cpi.pct_change if cpi else None
        core_cpi_val = core_cpi.pct_change if core_cpi else None
        pce_val = pce.pct_change if pce else None
        core_pce_val = core_pce.pct_change if core_pce else None
        be_5y_val = be_5y.latest_value if be_5y else None
        be_10y_val = be_10y.latest_value if be_10y else None

        # Determine trend
        if core_pce and core_pce.change:
            if core_pce.change > 0.1:
                trend = "rising"
            elif core_pce.change < -0.1:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        # Generate assessment
        fed_target = 2.0
        current = core_pce_val or cpi_val or 0

        if current > fed_target + 1:
            assessment = f"Inflation remains elevated at {current:.1f}%, well above the Fed's 2% target. Policy likely to remain restrictive."
        elif current > fed_target:
            assessment = f"Inflation at {current:.1f}% is moderating but still above target. Fed maintaining vigilance."
        elif current < fed_target - 0.5:
            assessment = f"Inflation at {current:.1f}% is below target. Potential room for policy easing."
        else:
            assessment = f"Inflation at {current:.1f}% is near the Fed's 2% target. Policy flexibility increases."

        return InflationAnalysis(
            headline_cpi=cpi_val,
            core_cpi=core_cpi_val,
            pce=pce_val,
            core_pce=core_pce_val,
            breakeven_5y=be_5y_val,
            breakeven_10y=be_10y_val,
            trend=trend,
            assessment=assessment,
        )

    def _analyze_us_growth(self, data: dict) -> GrowthAnalysis:
        """Analyze US growth data."""
        gdp_growth = data.get("gdp_growth")
        real_gdp = data.get("real_gdp")

        gdp_growth_val = gdp_growth.latest_value if gdp_growth else None
        real_gdp_val = real_gdp.latest_value if real_gdp else None

        # Determine trend
        if gdp_growth and gdp_growth.change:
            if gdp_growth.change > 0.2:
                trend = "accelerating"
            elif gdp_growth.change < -0.2:
                trend = "decelerating"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        # Generate assessment
        growth = gdp_growth_val or 0
        if growth > 3:
            assessment = f"Strong economic growth at {growth:.1f}% QoQ. Economy firing on all cylinders."
        elif growth > 2:
            assessment = f"Solid growth at {growth:.1f}% QoQ. Economy maintaining above-trend expansion."
        elif growth > 0:
            assessment = f"Moderate growth at {growth:.1f}% QoQ. Economy expanding but losing momentum."
        else:
            assessment = f"Negative growth at {growth:.1f}% QoQ. Recession concerns elevated."

        return GrowthAnalysis(
            gdp_growth=gdp_growth_val,
            real_gdp=real_gdp_val,
            trend=trend,
            assessment=assessment,
        )

    def _analyze_us_labor(self, data: dict) -> LaborAnalysis:
        """Analyze US labor market data."""
        unemployment = data.get("unemployment")
        payrolls = data.get("nonfarm_payrolls")
        claims = data.get("initial_claims")

        unemp_val = unemployment.latest_value if unemployment else None
        payrolls_val = payrolls.change if payrolls else None
        claims_val = claims.latest_value if claims else None

        # Determine trend
        if unemployment and unemployment.change:
            if unemployment.change > 0.2:
                trend = "weakening"
            elif unemployment.change < -0.1:
                trend = "strengthening"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        # Generate assessment
        unemp = unemp_val or 0
        if unemp < 4:
            assessment = f"Labor market remains tight with {unemp:.1f}% unemployment. Wage pressures likely."
        elif unemp < 5:
            assessment = f"Labor market balanced at {unemp:.1f}% unemployment. Healthy job market."
        else:
            assessment = f"Labor market softening with {unemp:.1f}% unemployment. Slack emerging."

        return LaborAnalysis(
            unemployment=unemp_val,
            nonfarm_payrolls=payrolls_val,
            initial_claims=claims_val,
            trend=trend,
            assessment=assessment,
        )

    def _analyze_us_monetary(
        self, rates: dict, yield_curve: dict
    ) -> MonetaryPolicyAnalysis:
        """Analyze US monetary policy."""
        fed_funds = rates.get("fed_funds")
        t2y = rates.get("treasury_2y")
        t10y = rates.get("treasury_10y")

        ff_val = fed_funds.latest_value if fed_funds else None
        t2y_val = t2y.latest_value if t2y else None
        t10y_val = t10y.latest_value if t10y else None
        spread = yield_curve.get("spread_2s10s")

        # Determine policy stance
        if ff_val and ff_val > 4:
            stance = "hawkish"
        elif ff_val and ff_val < 2:
            stance = "dovish"
        else:
            stance = "neutral"

        # Generate assessment
        if spread is not None and spread < 0:
            curve_msg = f"Yield curve inverted ({spread:.0f}bps). Recession signal historically."
        elif spread is not None and spread < 0.5:
            curve_msg = f"Yield curve flat ({spread:.0f}bps). Late-cycle dynamics."
        elif spread is not None:
            curve_msg = f"Yield curve normal ({spread:.0f}bps)."
        else:
            curve_msg = "Yield curve data unavailable."

        if ff_val is not None:
            assessment = f"Fed Funds at {ff_val:.2f}% ({stance} stance). {curve_msg}"
        else:
            assessment = f"Fed Funds data unavailable ({stance} stance). {curve_msg}"

        return MonetaryPolicyAnalysis(
            fed_funds=ff_val,
            treasury_2y=t2y_val,
            treasury_10y=t10y_val,
            spread_2s10s=spread,
            policy_stance=stance,
            assessment=assessment,
        )

    def _generate_us_assessment(
        self,
        inflation: InflationAnalysis,
        growth: GrowthAnalysis,
        labor: LaborAnalysis,
        monetary: MonetaryPolicyAnalysis,
    ) -> tuple[str, list[str], list[str]]:
        """Generate overall US macro assessment."""
        risks = []
        opportunities = []

        # Build narrative
        components = []

        if growth.gdp_growth and growth.gdp_growth > 2:
            components.append("solid growth")
            opportunities.append("Cyclical sectors may outperform")
        elif growth.gdp_growth and growth.gdp_growth < 1:
            components.append("slowing growth")
            risks.append("Growth deceleration could pressure earnings")

        if inflation.core_pce and inflation.core_pce > 3:
            components.append("elevated inflation")
            risks.append("Sticky inflation may delay Fed pivot")
        elif inflation.core_pce and inflation.core_pce < 2.5:
            components.append("moderating inflation")
            opportunities.append("Disinflation supports duration")

        if labor.unemployment and labor.unemployment < 4:
            components.append("tight labor market")
        elif labor.unemployment and labor.unemployment > 5:
            components.append("rising unemployment")
            risks.append("Labor market weakness could signal recession")

        if monetary.spread_2s10s and monetary.spread_2s10s < 0:
            risks.append("Inverted yield curve - historical recession indicator")

        narrative = ", ".join(components) if components else "mixed conditions"
        overall = f"US economy showing {narrative}. {monetary.assessment}"

        if not risks:
            risks.append("Geopolitical uncertainty")
        if not opportunities:
            opportunities.append("Policy pivot potential if inflation cools")

        return overall, risks, opportunities

    async def analyze_eu(self, us: RegionalAnalysis | None = None) -> RegionalAnalysis:
        """Analyze EU macro conditions based on US data and regime inference.

        Uses US macro conditions as a proxy since no direct ECB data source is
        available.  When US inflation is elevated, EU likely faces similar pressures
        from global commodity prices.  When US growth decelerates, EU — with its
        larger trade exposure — is typically hit harder.
        """
        # Derive EU picture from US data when available
        if us and us.inflation:
            us_inf = us.inflation.to_dict()
            cpi = us_inf.get("headline_cpi")
            trend = us_inf.get("trend", "stable")
        else:
            cpi = None
            trend = "unknown"

        if us and us.monetary_policy:
            us_policy = us.monetary_policy.to_dict()
            us_stance = us_policy.get("policy_stance", "neutral")
        else:
            us_stance = "neutral"

        # Construct assessment dynamically
        if cpi is not None and cpi > 3:
            inf_msg = f"European inflation likely elevated alongside US ({cpi:.1f}% CPI), driven by global energy and food prices"
            ecb_msg = "ECB likely maintaining restrictive stance, though fragmentation risk limits aggressive tightening"
        elif cpi is not None and cpi < 2:
            inf_msg = "Disinflationary pressures may be even stronger in Europe given weaker domestic demand"
            ecb_msg = "ECB has scope for easing ahead of the Fed, creating potential policy divergence"
        else:
            inf_msg = "European inflation trajectory broadly tracking US disinflation path with a lag"
            ecb_msg = "ECB balancing price stability with growth concerns — data-dependent stance"

        if us and us.growth:
            us_growth = us.growth.to_dict()
            gdp = us_growth.get("gdp_growth")
            if gdp is not None and gdp < 1:
                growth_msg = f"With US growth at {gdp:.1f}%, Europe's export-oriented economy faces significant headwinds"
            elif gdp is not None and gdp > 2:
                growth_msg = f"US strength ({gdp:.1f}%) provides a tailwind for European exporters, though domestic demand remains subdued"
            else:
                growth_msg = "European growth outlook mixed — manufacturing weakness offset by services resilience"
        else:
            growth_msg = "European growth remains structurally below US, with manufacturing sector under pressure"

        overall = f"{inf_msg}. {growth_msg}. {ecb_msg}."

        # Dynamic risks based on US conditions
        risks = []
        opportunities = []

        if us_stance == "hawkish":
            risks.append("ECB forced to follow Fed tightening, amplifying growth headwinds in periphery")
            risks.append("Sovereign spread widening in Italy/Greece if rates stay higher for longer")
        else:
            opportunities.append("ECB easing cycle could support European equities — relative value vs expensive US")

        risks.append("Energy security and industrial competitiveness remain structural challenges")
        risks.append("Geopolitical spillovers from Eastern Europe and trade policy uncertainty")

        if trend == "falling":
            opportunities.append("Disinflation opens door for ECB rate cuts, supporting duration-sensitive sectors")
        opportunities.append("Green transition capex cycle provides multi-year investment theme")
        opportunities.append("EUR undervaluation relative to PPP creates currency tailwind for EUR-denominated assets")

        return RegionalAnalysis(
            region="EU",
            inflation=None,
            growth=None,
            labor=None,
            monetary_policy=None,
            overall_assessment=overall,
            key_risks=risks,
            key_opportunities=opportunities,
        )

    async def analyze_asia(self, us: RegionalAnalysis | None = None) -> RegionalAnalysis:
        """Analyze Asia macro conditions derived from US data and global context.

        Japan policy normalisation, China stimulus trajectory, and EM Asia growth
        are all influenced by US rate cycle and dollar dynamics.
        """
        if us and us.monetary_policy:
            us_policy = us.monetary_policy.to_dict()
            ff = us_policy.get("fed_funds")
            us_stance = us_policy.get("policy_stance", "neutral")
        else:
            ff = None
            us_stance = "neutral"

        if us and us.growth:
            us_gdp = us.growth.to_dict().get("gdp_growth")
        else:
            us_gdp = None

        # Japan narrative
        if ff is not None and ff > 4:
            japan_msg = "BoJ normalization constrained by wide US-Japan rate differential — USD/JPY intervention risk elevated"
        elif ff is not None and ff < 3:
            japan_msg = "Narrowing US-Japan rate gap supports yen; BoJ has room to continue gradual normalization"
        else:
            japan_msg = "BoJ treading carefully — balancing domestic reflation against global rate dynamics"

        # China narrative
        if us_gdp is not None and us_gdp < 1.5:
            china_msg = "Weakening global demand pressures China's export engine, increasing urgency for domestic stimulus"
        elif us_gdp is not None and us_gdp > 2.5:
            china_msg = "Resilient US demand provides a floor for China trade, but property sector remains the binding constraint"
        else:
            china_msg = "China navigating between stimulus-driven stabilization and structural property sector deleveraging"

        # EM Asia
        if us_stance == "hawkish":
            em_msg = "Hawkish Fed pressures EM Asian currencies and limits policy easing scope"
        elif us_stance == "dovish":
            em_msg = "Dovish Fed creates room for EM Asian central banks to ease, supporting growth"
        else:
            em_msg = "EM Asia benefits from supply chain diversification and improving terms of trade"

        overall = f"{japan_msg}. {china_msg}. {em_msg}."

        risks = []
        opportunities = []

        if us_stance == "hawkish":
            risks.append("Strong USD pressures EM Asian currencies and tightens financial conditions")
        risks.append("China property sector stress could trigger disorderly deleveraging")
        risks.append("BoJ policy normalization may drain global liquidity if JGB yields spike")
        risks.append("Geopolitical tensions in Taiwan Strait remain underpriced tail risk")

        if us_stance in ("dovish", "neutral"):
            opportunities.append("Fed pivot supports EM Asian assets — rates and equities")
        opportunities.append("India and ASEAN capturing manufacturing share from China — secular growth theme")
        opportunities.append("Japan corporate governance reforms driving shareholder returns")

        return RegionalAnalysis(
            region="Asia",
            inflation=None,
            growth=None,
            labor=None,
            monetary_policy=None,
            overall_assessment=overall,
            key_risks=risks,
            key_opportunities=opportunities,
        )

    async def full_analysis(self) -> MacroAnalysis:
        """Perform complete macro analysis across all regions."""
        us = await self.analyze_us()
        eu = await self.analyze_eu(us)
        asia = await self.analyze_asia(us)

        global_outlook = self._generate_global_outlook(us, eu, asia)
        themes = self._identify_cross_regional_themes(us, eu, asia)

        return MacroAnalysis(
            us=us,
            eu=eu,
            asia=asia,
            global_outlook=global_outlook,
            cross_regional_themes=themes,
        )

    def _generate_global_outlook(
        self,
        us: RegionalAnalysis,
        eu: RegionalAnalysis,
        asia: RegionalAnalysis,
    ) -> str:
        """Generate global macro outlook from actual regional data."""
        parts = []

        # US leadership assessment
        if us.growth and us.growth.gdp_growth is not None:
            gdp = us.growth.gdp_growth
            if gdp > 2:
                parts.append(f"US economy leading global growth at {gdp:.1f}%, providing a floor for risk assets")
            elif gdp > 0:
                parts.append(f"US growth moderating to {gdp:.1f}%, losing its role as the global growth engine")
            else:
                parts.append(f"US contraction ({gdp:.1f}%) signals potential global synchronized downturn")

        # Policy stance
        if us.monetary_policy:
            stance = us.monetary_policy.policy_stance
            if stance == "hawkish":
                parts.append("Restrictive Fed policy continues to tighten global financial conditions via the dollar channel")
            elif stance == "dovish":
                parts.append("Fed easing cycle loosens global conditions, providing relief to dollar-sensitive economies")
            else:
                parts.append("Fed on hold — global policy divergence widening as ECB and BoJ chart separate paths")

        # Inflation
        if us.inflation and us.inflation.core_pce is not None:
            pce = us.inflation.core_pce
            trend = us.inflation.trend
            if pce > 3:
                parts.append(f"Persistent inflation ({pce:.1f}% core PCE, trend: {trend}) constrains policy flexibility globally")
            elif pce < 2.5 and trend == "falling":
                parts.append(f"Disinflation progress ({pce:.1f}% core PCE, trend: {trend}) creates room for synchronized easing")

        if not parts:
            parts.append("Global economy navigating uncertainty — mixed signals across growth, inflation, and policy")

        return ". ".join(parts) + "."

    def _identify_cross_regional_themes(
        self,
        us: RegionalAnalysis,
        eu: RegionalAnalysis,
        asia: RegionalAnalysis,
    ) -> list[str]:
        """Identify themes from actual regional analysis data."""
        themes = []

        # Policy divergence/convergence
        if us.monetary_policy:
            stance = us.monetary_policy.policy_stance
            if stance == "hawkish":
                themes.append("Central bank divergence — Fed hawkish while others face growth constraints")
            elif stance == "dovish":
                themes.append("Synchronized easing cycle — global liquidity conditions improving")
            else:
                themes.append("Central bank pause — markets transitioning from rate regime to data-dependent trading")

        # Inflation regime
        if us.inflation and us.inflation.trend == "falling":
            themes.append("Global disinflation — supply chain normalization and base effects driving price deceleration")
        elif us.inflation and us.inflation.trend == "rising":
            themes.append("Inflation re-acceleration risk — commodity prices and wage stickiness challenging central bank credibility")

        # Growth
        if us.growth and us.growth.gdp_growth is not None:
            if us.growth.gdp_growth < 1:
                themes.append("Global growth scare — leading indicators deteriorating across regions")
            elif us.growth.gdp_growth > 2.5:
                themes.append("Resilient growth despite tight policy — soft landing narrative gaining traction")

        # Always-relevant structural themes
        themes.append("AI and technology capex cycle reshaping productivity assumptions and sector leadership")
        themes.append("Geopolitical fragmentation driving supply chain reshoring and defense spending")

        return themes[:5]
