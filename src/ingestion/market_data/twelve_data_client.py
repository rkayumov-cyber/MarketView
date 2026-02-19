"""Live market data layer: Twelve Data (crypto) + yfinance (everything else).

Twelve Data free tier: 8 credits/min, each symbol = 1 credit.
We use TD only for crypto (6 credits/call) to stay within limits.
Everything else (equities, FX, commodities, indices) uses yfinance directly,
bypassing the broken Redis cache serialization in base.py.
All results use plain dicts + in-memory TTL cache.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.twelvedata.com"

# --- Twelve Data symbol mappings (only symbols that work on free tier) ---

FX_SYMBOLS = {
    "eurusd": "EUR/USD",
    "usdjpy": "USD/JPY",
    "gbpusd": "GBP/USD",
    "usdchf": "USD/CHF",
    "audusd": "AUD/USD",
    "usdcad": "USD/CAD",
    "usdcnh": "USD/CNH",
    "usdmxn": "USD/MXN",
    "usdbrl": "USD/BRL",
}

COMMODITY_SYMBOLS = {
    "gold": "XAU/USD",
    "silver": "XAG/USD",
    "wti_crude": "WTI",
    "brent_crude": "BRENT",
    "natural_gas": "NATGAS",
    "copper": "COPPER",
    "corn": "CORN",
    "wheat": "WHEAT",
    "soybeans": "SOYBEANS",
}

CRYPTO_SYMBOLS = {
    "bitcoin": "BTC/USD",
    "ethereum": "ETH/USD",
    "solana": "SOL/USD",
    "bnb": "BNB/USD",
    "xrp": "XRP/USD",
    "cardano": "ADA/USD",
}

DISPLAY_NAMES = {
    "XAU/USD": "Gold",
    "XAG/USD": "Silver",
    "WTI": "Crude Oil WTI",
    "BRENT": "Crude Oil Brent",
    "NATGAS": "Natural Gas",
    "COPPER": "Copper",
    "CORN": "Corn",
    "WHEAT": "Wheat",
    "SOYBEANS": "Soybeans",
    "BTC/USD": "Bitcoin",
    "ETH/USD": "Ethereum",
    "SOL/USD": "Solana",
    "BNB/USD": "BNB",
    "XRP/USD": "XRP",
    "ADA/USD": "Cardano",
}

_TD_TO_INTERNAL: dict[str, str] = {}
for _mapping in [FX_SYMBOLS, COMMODITY_SYMBOLS, CRYPTO_SYMBOLS]:
    for _key, _td_sym in _mapping.items():
        _TD_TO_INTERNAL[_td_sym] = _key

# --- yfinance symbol mappings (for indices that TD free tier can't do) ---

YFINANCE_INDICES = {
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

SECTOR_ETFS = {
    "technology": "XLK",
    "healthcare": "XLV",
    "financials": "XLF",
    "consumer_discretionary": "XLY",
    "consumer_staples": "XLP",
    "industrials": "XLI",
    "energy": "XLE",
    "materials": "XLB",
    "utilities": "XLU",
    "real_estate": "XLRE",
    "communication": "XLC",
}

YFINANCE_FX = {
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

YFINANCE_COMMODITIES = {
    "gold": ("GC=F", "Gold Futures", "precious_metals"),
    "silver": ("SI=F", "Silver Futures", "precious_metals"),
    "wti_crude": ("CL=F", "Crude Oil WTI", "energy"),
    "brent_crude": ("BZ=F", "Crude Oil Brent", "energy"),
    "natural_gas": ("NG=F", "Natural Gas Futures", "energy"),
    "copper": ("HG=F", "Copper Futures", "industrial"),
    "corn": ("ZC=F", "Corn Futures", "agriculture"),
    "wheat": ("ZW=F", "Wheat Futures", "agriculture"),
    "soybeans": ("ZS=F", "Soybean Futures", "agriculture"),
}

# Cache TTL in seconds
CACHE_TTL = 300  # 5 minutes


class _MemCache:
    """Simple in-memory TTL cache."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, val = entry
        if time.time() - ts > CACHE_TTL:
            del self._store[key]
            return None
        return val

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)


_cache = _MemCache()


# ============================================================
# Twelve Data helpers
# ============================================================

async def _fetch_quotes(symbols: list[str]) -> dict[str, dict]:
    """Batch-fetch quotes from Twelve Data /quote endpoint."""
    api_key = settings.twelve_data_api_key
    if not api_key:
        raise ValueError("TWELVE_DATA_API_KEY not configured")

    symbol_str = ",".join(symbols)
    params = {"symbol": symbol_str, "apikey": api_key}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/quote", params=params)
        resp.raise_for_status()
        data = resp.json()

    results: dict[str, dict] = {}

    if len(symbols) == 1:
        if data.get("status") == "error":
            logger.warning("Twelve Data error for %s: %s", symbols[0], data.get("message"))
            return results
        results[symbols[0]] = data
        return results

    for sym in symbols:
        quote = data.get(sym)
        if quote and quote.get("status") != "error":
            results[sym] = quote
        else:
            logger.debug("Twelve Data: no data for %s", sym)

    return results


def _pf(val: Any) -> float | None:
    """Safely parse a value to float."""
    if val is None or val == "" or val == "null":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _td_to_fx(td_symbol: str, q: dict) -> dict:
    """Convert a Twelve Data quote to the FX pair dict shape."""
    pair_key = td_symbol.replace("/", "")
    return {
        "pair": pair_key,
        "rate": _pf(q.get("close")),
        "change": _pf(q.get("change")),
        "change_percent": _pf(q.get("percent_change")),
        "day_high": _pf(q.get("high")),
        "day_low": _pf(q.get("low")),
        "fifty_two_week_high": _pf(q.get("fifty_two_week", {}).get("high")) if isinstance(q.get("fifty_two_week"), dict) else None,
        "fifty_two_week_low": _pf(q.get("fifty_two_week", {}).get("low")) if isinstance(q.get("fifty_two_week"), dict) else None,
        "timestamp": q.get("datetime", ""),
    }


def _td_to_commodity(td_symbol: str, q: dict) -> dict:
    """Convert a Twelve Data quote to the commodity dict shape."""
    internal_key = _TD_TO_INTERNAL.get(td_symbol, td_symbol)
    volume = _pf(q.get("volume"))
    return {
        "symbol": internal_key,
        "name": q.get("name") or DISPLAY_NAMES.get(td_symbol, td_symbol),
        "price": _pf(q.get("close")),
        "change": _pf(q.get("change")),
        "change_percent": _pf(q.get("percent_change")),
        "day_high": _pf(q.get("high")),
        "day_low": _pf(q.get("low")),
        "volume": int(volume) if volume else 0,
        "fifty_two_week_high": _pf(q.get("fifty_two_week", {}).get("high")) if isinstance(q.get("fifty_two_week"), dict) else None,
        "fifty_two_week_low": _pf(q.get("fifty_two_week", {}).get("low")) if isinstance(q.get("fifty_two_week"), dict) else None,
        "timestamp": q.get("datetime", ""),
    }


def _td_to_crypto(td_symbol: str, q: dict) -> dict:
    """Convert a Twelve Data quote to the crypto dict shape."""
    internal_key = _TD_TO_INTERNAL.get(td_symbol, td_symbol)
    id_map = {"bitcoin": "bitcoin", "ethereum": "ethereum", "solana": "solana",
              "bnb": "binancecoin", "xrp": "ripple", "cardano": "cardano"}
    sym_map = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
               "bnb": "BNB", "xrp": "XRP", "cardano": "ADA"}
    volume = _pf(q.get("volume"))
    return {
        "id": id_map.get(internal_key, internal_key),
        "symbol": sym_map.get(internal_key, td_symbol),
        "name": q.get("name") or DISPLAY_NAMES.get(td_symbol, td_symbol),
        "current_price": _pf(q.get("close")),
        "market_cap": None,
        "market_cap_rank": None,
        "total_volume": int(volume) if volume else None,
        "high_24h": _pf(q.get("high")),
        "low_24h": _pf(q.get("low")),
        "price_change_24h": _pf(q.get("change")),
        "price_change_percentage_24h": _pf(q.get("percent_change")),
        "price_change_percentage_7d": None,
        "price_change_percentage_30d": None,
        "circulating_supply": None,
        "total_supply": None,
        "ath": None,
        "ath_change_percentage": None,
        "atl": None,
        "timestamp": q.get("datetime", ""),
    }


# ============================================================
# Direct yfinance helpers (bypass Redis, return plain dicts)
# ============================================================

async def _yf_quote(symbol: str) -> dict | None:
    """Fetch a single yfinance quote as a plain dict."""
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        info = await asyncio.to_thread(lambda: ticker.info)
        price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose", price)
        change = price - prev if price and prev else 0
        pct = (change / prev * 100) if prev else 0
        return {
            "symbol": symbol,
            "name": info.get("shortName", info.get("longName", symbol)),
            "current_price": price,
            "previous_close": prev,
            "open_price": info.get("regularMarketOpen", info.get("open", 0)),
            "day_high": info.get("regularMarketDayHigh", info.get("dayHigh", 0)),
            "day_low": info.get("regularMarketDayLow", info.get("dayLow", 0)),
            "volume": info.get("regularMarketVolume", info.get("volume", 0)) or 0,
            "change": round(change, 4),
            "change_percent": round(pct, 4),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.warning("yfinance quote failed for %s: %s", symbol, e)
        return None


async def _yf_dxy() -> dict | None:
    """Fetch DXY from yfinance as a plain dict."""
    import yfinance as yf

    try:
        ticker = yf.Ticker("DX-Y.NYB")
        info = await asyncio.to_thread(lambda: ticker.info)
        value = info.get("regularMarketPrice") or info.get("ask", 0)
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose", value)
        change = value - prev if value and prev else 0
        pct = (change / prev * 100) if prev else 0
        return {
            "value": value,
            "change": round(change, 4),
            "change_percent": round(pct, 4),
            "day_high": info.get("regularMarketDayHigh", info.get("dayHigh", 0)),
            "day_low": info.get("regularMarketDayLow", info.get("dayLow", 0)),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.warning("yfinance DXY fetch failed: %s", e)
        return None


async def _yf_fx_pair(pair_name: str, symbol: str) -> dict | None:
    """Fetch a single FX pair from yfinance as a plain dict."""
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        info = await asyncio.to_thread(lambda: ticker.info)
        rate = info.get("regularMarketPrice") or info.get("ask", 0)
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose", rate)
        change = rate - prev if rate and prev else 0
        pct = (change / prev * 100) if prev else 0
        return {
            "pair": pair_name.upper(),
            "rate": rate,
            "change": round(change, 6),
            "change_percent": round(pct, 4),
            "day_high": info.get("regularMarketDayHigh", info.get("dayHigh", 0)),
            "day_low": info.get("regularMarketDayLow", info.get("dayLow", 0)),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.warning("yfinance FX pair %s failed: %s", pair_name, e)
        return None


async def _yf_commodity(key: str, symbol: str, name: str) -> dict | None:
    """Fetch a single commodity from yfinance as a plain dict."""
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        info = await asyncio.to_thread(lambda: ticker.info)
        price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose", price)
        change = price - prev if price and prev else 0
        pct = (change / prev * 100) if prev else 0
        volume = info.get("regularMarketVolume") or info.get("volume", 0) or 0
        return {
            "symbol": key,
            "name": name,
            "price": price,
            "change": round(change, 4),
            "change_percent": round(pct, 4),
            "day_high": info.get("regularMarketDayHigh", info.get("dayHigh", 0)),
            "day_low": info.get("regularMarketDayLow", info.get("dayLow", 0)),
            "volume": volume,
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.warning("yfinance commodity %s failed: %s", key, e)
        return None


# ============================================================
# Public fetch functions (used by market router)
# ============================================================

async def fetch_snapshot() -> dict[str, Any]:
    """Fetch quick snapshot: SPX, VIX, DXY from yfinance; BTC, Gold from Twelve Data."""
    cache_key = "live:snapshot"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    # Run yfinance (indices) and Twelve Data (crypto/commodities) in parallel
    td_symbols = ["BTC/USD", "XAU/USD"]
    yf_tasks = {
        "spx": _yf_quote("^GSPC"),
        "vix": _yf_quote("^VIX"),
        "dxy": _yf_dxy(),
    }

    td_task = _fetch_quotes(td_symbols)

    all_results = await asyncio.gather(
        *yf_tasks.values(),
        td_task,
        return_exceptions=True,
    )

    yf_results = dict(zip(yf_tasks.keys(), all_results[:3]))
    td_quotes = all_results[3] if not isinstance(all_results[3], Exception) else {}

    result: dict[str, Any] = {}

    # yfinance results
    for key in ("spx", "vix", "dxy"):
        val = yf_results.get(key)
        if isinstance(val, dict):
            result[key] = val

    # Twelve Data results
    if isinstance(td_quotes, dict):
        if "BTC/USD" in td_quotes:
            result["bitcoin"] = _td_to_crypto("BTC/USD", td_quotes["BTC/USD"])
        if "XAU/USD" in td_quotes:
            result["gold"] = _td_to_commodity("XAU/USD", td_quotes["XAU/USD"])

    result["yield_curve"] = None

    if result:
        _cache.set(cache_key, result)
    return result


async def fetch_equities() -> dict[str, Any]:
    """Fetch US + global equity indices and sectors via yfinance."""
    cache_key = "live:equities"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    us_keys = ["spx", "nasdaq", "dow", "russell2000"]
    global_keys = ["nikkei", "eurostoxx50", "ftse100", "dax", "hang_seng", "shanghai", "nifty50"]

    # Build all tasks
    tasks: dict[str, Any] = {}
    for key in us_keys + global_keys + ["vix"]:
        tasks[key] = _yf_quote(YFINANCE_INDICES[key])
    for sector, etf in SECTOR_ETFS.items():
        tasks[f"sector_{sector}"] = _yf_quote(etf)

    all_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    result_map = dict(zip(tasks.keys(), all_results))

    us: dict[str, dict] = {}
    for key in us_keys:
        val = result_map.get(key)
        if isinstance(val, dict):
            us[key] = val

    global_indices: dict[str, dict] = {}
    for key in global_keys:
        val = result_map.get(key)
        if isinstance(val, dict):
            global_indices[key] = val

    sectors: dict[str, float] = {}
    for sector in SECTOR_ETFS:
        val = result_map.get(f"sector_{sector}")
        if isinstance(val, dict):
            sectors[sector] = val.get("change_percent", 0)

    vix_val = result_map.get("vix")
    vix_data = vix_val if isinstance(vix_val, dict) else None

    result = {
        "us": us,
        "global": global_indices,
        "sectors": sectors,
        "vix": vix_data,
    }

    if us:
        _cache.set(cache_key, result)
    return result


async def fetch_fx() -> dict[str, Any]:
    """Fetch FX pairs and DXY from yfinance."""
    cache_key = "live:fx"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    # All yfinance — no TD credits used
    tasks: dict[str, Any] = {}
    for key, symbol in YFINANCE_FX.items():
        tasks[key] = _yf_fx_pair(key, symbol)
    tasks["dxy"] = _yf_dxy()

    all_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    result_map = dict(zip(tasks.keys(), all_results))

    pairs: dict[str, dict] = {}
    for key in YFINANCE_FX:
        val = result_map.get(key)
        if isinstance(val, dict):
            pairs[key] = val

    dxy = result_map.get("dxy") if isinstance(result_map.get("dxy"), dict) else None

    # Compute USD strength index
    usd_strength_vals = []
    for key, pair_data in pairs.items():
        pct = pair_data.get("change_percent")
        if pct is not None:
            if key.startswith("usd"):
                usd_strength_vals.append(pct)
            else:
                usd_strength_vals.append(-pct)
    avg_usd = sum(usd_strength_vals) / len(usd_strength_vals) if usd_strength_vals else None

    result = {
        "dxy": dxy,
        "pairs": pairs,
        "usd_strength_index": round(avg_usd, 4) if avg_usd is not None else None,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if pairs:
        _cache.set(cache_key, result)
    return result


async def fetch_commodities() -> dict[str, Any]:
    """Fetch commodity prices from yfinance."""
    cache_key = "live:commodities"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    # All yfinance — no TD credits used
    tasks: dict[str, Any] = {}
    for key, (symbol, name, _) in YFINANCE_COMMODITIES.items():
        tasks[key] = _yf_commodity(key, symbol, name)

    all_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    result_map = dict(zip(tasks.keys(), all_results))

    precious: dict[str, dict] = {}
    energy: dict[str, dict] = {}
    agriculture: dict[str, dict] = {}
    industrial: dict[str, dict] = {}

    category_buckets = {
        "precious_metals": precious,
        "energy": energy,
        "agriculture": agriculture,
        "industrial": industrial,
    }

    for key, (_, _, category) in YFINANCE_COMMODITIES.items():
        val = result_map.get(key)
        if isinstance(val, dict):
            category_buckets[category][key] = val

    result = {
        "precious_metals": precious,
        "energy": energy,
        "agriculture": agriculture,
        "industrial": industrial,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if precious or energy:
        _cache.set(cache_key, result)
    return result


async def fetch_crypto() -> dict[str, Any]:
    """Fetch crypto prices from Twelve Data."""
    cache_key = "live:crypto"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    quotes = await _fetch_quotes(list(CRYPTO_SYMBOLS.values()))

    id_map = {"bitcoin": "bitcoin", "ethereum": "ethereum", "solana": "solana",
              "bnb": "binancecoin", "xrp": "ripple", "cardano": "cardano"}

    assets: dict[str, dict] = {}
    for key, td_sym in CRYPTO_SYMBOLS.items():
        asset_key = id_map.get(key, key)
        if td_sym in quotes:
            assets[asset_key] = _td_to_crypto(td_sym, quotes[td_sym])

    result = {
        "assets": assets,
        "market_overview": None,
        "fear_greed": None,
    }

    if assets:
        _cache.set(cache_key, result)
    return result
