"""Pydantic models for report structures."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportLevel(int, Enum):
    """Report depth levels."""

    EXECUTIVE = 1
    STANDARD = 2
    DEEP_DIVE = 3


class ReportFormat(str, Enum):
    """Report output formats."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"
    HTML = "html"


class ReportConfig(BaseModel):
    """Configuration for report generation."""

    level: ReportLevel = ReportLevel.STANDARD
    format: ReportFormat = ReportFormat.MARKDOWN
    include_technicals: bool = True
    include_sentiment: bool = True
    include_correlations: bool = True
    include_research: bool = False
    custom_assets: list[str] | None = None
    document_ids: list[str] | None = None  # None = search all documents
    title: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    custom_prompt: str | None = None  # Free-text focus instructions for LLM


class MarketRegimeInfo(BaseModel):
    """Market regime information."""

    regime: str
    confidence: float
    description: str
    signals: list[str]


class SentimentInfo(BaseModel):
    """Sentiment analysis information."""

    overall_score: float
    bullish_ratio: float
    trending_tickers: list[tuple[str, int]]
    source: str = "reddit"


class DivergenceInfo(BaseModel):
    """Data vs sentiment divergence."""

    has_divergence: bool
    description: str
    data_signal: str
    sentiment_signal: str


class PulseSection(BaseModel):
    """The Pulse - Current market narrative section."""

    regime: MarketRegimeInfo
    sentiment: SentimentInfo | None = None
    divergences: list[DivergenceInfo] = Field(default_factory=list)
    big_narrative: str
    key_takeaways: list[str]


class SubredditBreakdown(BaseModel):
    """Per-subreddit sentiment breakdown."""

    subreddit: str
    sentiment_score: float
    bullish_ratio: float
    post_count: int
    top_tickers: list[tuple[str, int]] = Field(default_factory=list)


class SentimentSection(BaseModel):
    """Dedicated sentiment analysis section."""

    overall_score: float
    overall_label: str  # "Bullish", "Bearish", "Neutral"
    bullish_ratio: float
    total_posts: int
    subreddit_count: int
    trending_tickers: list[tuple[str, int]] = Field(default_factory=list)
    subreddit_breakdowns: list[SubredditBreakdown] = Field(default_factory=list)
    narrative: str
    contrarian_signals: list[str] = Field(default_factory=list)
    source: str = "reddit"


class RegionMacro(BaseModel):
    """Regional macro analysis."""

    region: str
    headline: str
    inflation: dict[str, Any] | None = None
    growth: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    risks: list[str]
    opportunities: list[str]


class MacroSection(BaseModel):
    """Macro analysis section."""

    us: RegionMacro | None = None
    eu: RegionMacro | None = None
    asia: RegionMacro | None = None
    global_outlook: str
    themes: list[str]


class AssetClassData(BaseModel):
    """Single asset class data."""

    asset_class: str
    headline: str
    data: dict[str, Any]
    key_levels: dict[str, float] | None = None
    commentary: str


class EquityData(AssetClassData):
    """Equity market data."""

    us_indices: dict[str, Any]
    global_indices: dict[str, Any]
    sectors: dict[str, float]
    vix: dict[str, Any] | None = None


class FixedIncomeData(AssetClassData):
    """Fixed income data."""

    yield_curve: dict[str, float | None]
    credit_spreads: dict[str, Any]
    curve_shape: str


class FXData(AssetClassData):
    """FX market data."""

    dxy: dict[str, Any] | None = None
    dm_pairs: dict[str, Any]
    em_pairs: dict[str, Any]
    usd_bias: str


class CommodityData(AssetClassData):
    """Commodity market data."""

    precious: dict[str, Any]
    energy: dict[str, Any]
    agriculture: dict[str, Any] | None = None


class CryptoData(AssetClassData):
    """Crypto market data."""

    major_coins: dict[str, Any]
    market_overview: dict[str, Any] | None = None
    fear_greed: dict[str, Any] | None = None


class AssetSection(BaseModel):
    """Asset class deep dive section."""

    equities: EquityData | None = None
    fixed_income: FixedIncomeData | None = None
    fx: FXData | None = None
    commodities: CommodityData | None = None
    crypto: CryptoData | None = None


class TechnicalLevel(BaseModel):
    """Technical level for an asset."""

    asset: str
    current_price: float
    support_1: float
    support_2: float
    resistance_1: float
    resistance_2: float
    pivot: float
    trend: str
    rsi: float
    signal: str


class VolatilityAnalysis(BaseModel):
    """Volatility analysis."""

    vix: float | None = None
    vix_percentile: float | None = None
    move_index: float | None = None
    assessment: str


class PositioningData(BaseModel):
    """Market positioning data."""

    retail_sentiment: str
    institutional_flows: str | None = None
    cot_summary: str | None = None


class CorrelationInsight(BaseModel):
    """Correlation insight."""

    pair: str
    correlation: float
    interpretation: str


class TechnicalsSection(BaseModel):
    """Technicals and positioning section."""

    key_levels: list[TechnicalLevel]
    volatility: VolatilityAnalysis
    positioning: PositioningData | None = None
    correlations: list[CorrelationInsight] | None = None


class EconomicEvent(BaseModel):
    """Upcoming economic event."""

    date: str
    event: str
    importance: str  # "high", "medium", "low"
    expected_impact: str


class OutlierEvent(BaseModel):
    """Low probability, high impact event."""

    event: str
    probability: str
    potential_impact: str
    hedging_idea: str | None = None


class ForwardSection(BaseModel):
    """Forward watch section."""

    lesson_of_the_day: str
    upcoming_events: list[EconomicEvent]
    outlier_event: OutlierEvent
    positioning_suggestions: list[str] | None = None


class ReportSection(BaseModel):
    """Generic report section."""

    title: str
    content: Any


class ResearchInsight(BaseModel):
    """A single research insight included in a report."""

    text: str
    source: str
    document_id: str
    page: int | None
    relevance_score: float
    section: str  # which report section this is relevant to


class ResearchInsightsSection(BaseModel):
    """Collection of research insights from uploaded documents."""

    insights: list[ResearchInsight]
    document_count: int
    total_chunks_searched: int


class PositioningSummaryItem(BaseModel):
    """Single row in the positioning summary table."""

    asset_class: str
    bias: str  # "Overweight", "Neutral", "Underweight"
    conviction: str  # "High", "Medium", "Low"
    rationale: str


class Report(BaseModel):
    """Complete market analysis report."""

    report_id: str
    title: str
    level: ReportLevel
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    config: ReportConfig

    executive_summary: str = ""
    thesis: str = ""
    positioning_summary: list[PositioningSummaryItem] = Field(default_factory=list)

    pulse: PulseSection
    sentiment: SentimentSection | None = None
    macro: MacroSection
    assets: AssetSection
    technicals: TechnicalsSection | None = None
    forward: ForwardSection
    research: ResearchInsightsSection | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
