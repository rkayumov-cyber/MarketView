"""Market constants and enumerations."""

from enum import Enum


class MarketRegime(str, Enum):
    """Market regime classification."""

    GOLDILOCKS = "goldilocks"  # Low inflation, steady growth
    INFLATIONARY_EXPANSION = "inflationary_expansion"  # High growth, rising inflation
    STAGFLATION = "stagflation"  # Low growth, high inflation
    DEFLATIONARY = "deflationary"  # Low growth, falling inflation
    RISK_OFF = "risk_off"  # Flight to safety
    RISK_ON = "risk_on"  # Risk appetite high


class AssetClass(str, Enum):
    """Asset class categories."""

    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    FX = "fx"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"


class ReportLevel(int, Enum):
    """Report depth levels."""

    EXECUTIVE = 1  # Bullet points, key levels
    STANDARD = 2  # Full breakdown with historical context
    DEEP_DIVE = 3  # Institutional-grade with correlations


class Region(str, Enum):
    """Geographic regions."""

    US = "us"
    EU = "eu"
    ASIA = "asia"
    EM = "em"  # Emerging markets
    GLOBAL = "global"


class Sector(str, Enum):
    """Equity sectors."""

    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIALS = "financials"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    INDUSTRIALS = "industrials"
    ENERGY = "energy"
    MATERIALS = "materials"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    COMMUNICATION = "communication"


# FRED Series IDs for key economic indicators
FRED_SERIES = {
    # Inflation
    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "pce": "PCEPI",
    "core_pce": "PCEPILFE",
    "breakeven_5y": "T5YIE",
    "breakeven_10y": "T10YIE",
    # Growth
    "gdp": "GDP",
    "real_gdp": "GDPC1",
    "gdp_growth": "A191RL1Q225SBEA",
    # Labor Market
    "unemployment": "UNRATE",
    "nonfarm_payrolls": "PAYEMS",
    "initial_claims": "ICSA",
    "continuing_claims": "CCSA",
    # Interest Rates
    "fed_funds": "FEDFUNDS",
    "treasury_2y": "DGS2",
    "treasury_10y": "DGS10",
    "treasury_30y": "DGS30",
    # Credit
    "hy_spread": "BAMLH0A0HYM2",
    "ig_spread": "BAMLC0A4CBBB",
    # Financial Conditions
    "financial_stress": "STLFSI4",
    "vix": "VIXCLS",
    # Dollar
    "dxy": "DTWEXBGS",
}

# Major market indices
INDICES = {
    "spx": "^GSPC",
    "nasdaq": "^IXIC",
    "dow": "^DJI",
    "russell2000": "^RUT",
    "vix": "^VIX",
    "nikkei": "^N225",
    "eurostoxx50": "^STOXX50E",
    "ftse100": "^FTSE",
    "dax": "^GDAXI",
    "hang_seng": "^HSI",
    "shanghai": "000001.SS",
    "nifty50": "^NSEI",
}

# FX pairs
FX_PAIRS = {
    "eurusd": "EURUSD=X",
    "usdjpy": "JPY=X",
    "gbpusd": "GBPUSD=X",
    "usdchf": "CHF=X",
    "audusd": "AUDUSD=X",
    "usdcad": "CAD=X",
    "usdcnh": "CNH=X",
    "usdmxn": "MXN=X",
    "usdbrl": "BRL=X",
}

# Commodities
COMMODITIES = {
    "gold": "GC=F",
    "silver": "SI=F",
    "wti_crude": "CL=F",
    "brent_crude": "BZ=F",
    "natural_gas": "NG=F",
    "copper": "HG=F",
    "corn": "ZC=F",
    "wheat": "ZW=F",
    "soybeans": "ZS=F",
}

# Crypto assets
CRYPTO_IDS = {
    "bitcoin": "bitcoin",
    "ethereum": "ethereum",
    "solana": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "cardano": "cardano",
}

# Reddit subreddits for sentiment
REDDIT_SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "cryptocurrency",
    "Bitcoin",
    "ethereum",
    "options",
    "SPACs",
]

# Technical analysis constants
TECHNICAL = {
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_period": 20,
    "bb_std": 2,
    "sma_short": 20,
    "sma_medium": 50,
    "sma_long": 200,
}
