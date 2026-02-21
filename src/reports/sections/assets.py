"""Asset section builder — regime-aware, cross-referencing commentary."""

from src.config.constants import MarketRegime
from src.ingestion.aggregator import DataAggregator
from src.analysis import RegimeDetector
from src.reports.models import (
    AssetSection,
    EquityData,
    FixedIncomeData,
    FXData,
    CommodityData,
    CryptoData,
    ReportLevel,
)

# Regime-sensitive thresholds: what counts as a "big move" depends on context
_MOVE_THRESHOLDS = {
    MarketRegime.GOLDILOCKS:             {"equity": 0.5, "vix_high": 20, "vix_low": 13, "fx": 0.2, "gold": 0.3, "oil": 0.7, "btc": 2},
    MarketRegime.INFLATIONARY_EXPANSION: {"equity": 0.7, "vix_high": 22, "vix_low": 15, "fx": 0.3, "gold": 0.5, "oil": 1.0, "btc": 3},
    MarketRegime.STAGFLATION:            {"equity": 0.5, "vix_high": 25, "vix_low": 18, "fx": 0.3, "gold": 0.4, "oil": 1.0, "btc": 3},
    MarketRegime.DEFLATIONARY:           {"equity": 0.5, "vix_high": 22, "vix_low": 15, "fx": 0.2, "gold": 0.3, "oil": 0.7, "btc": 2},
    MarketRegime.RISK_OFF:               {"equity": 1.0, "vix_high": 30, "vix_low": 20, "fx": 0.4, "gold": 0.5, "oil": 1.5, "btc": 4},
    MarketRegime.RISK_ON:                {"equity": 0.5, "vix_high": 18, "vix_low": 12, "fx": 0.2, "gold": 0.3, "oil": 0.7, "btc": 2},
}

# Which sectors should lead in each regime
_REGIME_SECTOR_LEADERS = {
    MarketRegime.GOLDILOCKS: ["technology", "consumer_discretionary", "communication_services"],
    MarketRegime.INFLATIONARY_EXPANSION: ["energy", "materials", "financials"],
    MarketRegime.STAGFLATION: ["consumer_staples", "utilities", "healthcare"],
    MarketRegime.DEFLATIONARY: ["technology", "consumer_staples", "utilities"],
    MarketRegime.RISK_OFF: ["consumer_staples", "utilities", "healthcare"],
    MarketRegime.RISK_ON: ["technology", "consumer_discretionary", "financials"],
}


class AssetSectionBuilder:
    """Builder for the Asset class deep dive section."""

    def __init__(self) -> None:
        self.aggregator = DataAggregator()
        self.regime_detector = RegimeDetector()

    async def build(self, level: ReportLevel) -> AssetSection:
        """Build the Asset section with regime-aware commentary."""
        snapshot = await self.aggregator.get_full_snapshot()

        # Detect regime for context-sensitive analysis
        regime_result = await self.regime_detector.detect_regime()
        regime = regime_result.regime
        thresholds = _MOVE_THRESHOLDS.get(regime, _MOVE_THRESHOLDS[MarketRegime.GOLDILOCKS])
        implications = self.regime_detector.get_regime_implications(regime)

        equities = self._build_equities(snapshot.equities, level, regime, thresholds, implications)
        fixed_income = self._build_fixed_income(snapshot.fixed_income, level, regime, implications)
        fx = self._build_fx(snapshot.fx, level, regime, thresholds, implications)
        commodities = self._build_commodities(snapshot.commodities, level, regime, thresholds, implications)
        crypto = self._build_crypto(snapshot.crypto, level, regime, thresholds, implications)

        return AssetSection(
            equities=equities,
            fixed_income=fixed_income,
            fx=fx,
            commodities=commodities,
            crypto=crypto,
        )

    # ── Equities ────────────────────────────────────────────

    def _build_equities(self, data: dict, level, regime, thresholds, impl) -> EquityData:
        us = data.get("us", {})
        global_indices = data.get("global", {})
        sectors = data.get("sectors", {})
        vix = data.get("vix")

        spx = us.get("spx", {})
        spx_change = spx.get("change_percent", 0) if spx else 0
        eq_thresh = thresholds["equity"]

        # Regime-aware headline
        regime_label = regime.value.replace("_", " ")
        if abs(spx_change) > eq_thresh:
            direction = "higher" if spx_change > 0 else "lower"
            headline = f"Equities pushing {direction} in {regime_label} regime — S&P 500 {spx_change:+.1f}%"
        else:
            headline = f"Equities range-bound as {regime_label} conditions persist — S&P 500 {spx_change:+.1f}%"

        commentary = self._equity_commentary(us, sectors, vix, level, regime, thresholds, impl)

        key_levels = {}
        if spx:
            key_levels["SPX"] = spx.get("current_price", 0)
        if "nasdaq" in us:
            key_levels["NDX"] = us["nasdaq"].get("current_price", 0)

        return EquityData(
            asset_class="equity",
            headline=headline,
            data=data,
            key_levels=key_levels,
            commentary=commentary,
            us_indices=us,
            global_indices=global_indices,
            sectors=sectors,
            vix=vix,
        )

    def _equity_commentary(self, us, sectors, vix, level, regime, thresholds, impl) -> str:
        parts = []

        # Core price action
        spx = us.get("spx", {})
        ndx = us.get("nasdaq", {})
        if spx:
            parts.append(
                f"S&P 500 at {spx.get('current_price', 0):,.0f} "
                f"({spx.get('change_percent', 0):+.2f}%)"
            )

        # SPX vs NASDAQ divergence
        if spx and ndx:
            spx_chg = spx.get("change_percent", 0)
            ndx_chg = ndx.get("change_percent", 0)
            spread = ndx_chg - spx_chg
            if abs(spread) > 0.5:
                if spread > 0:
                    parts.append("Growth/tech outperforming value — risk appetite tilting toward duration-sensitive names")
                else:
                    parts.append("Broad market outperforming tech — rotation into cyclicals/value suggests shifting growth expectations")

        # VIX — regime-sensitive interpretation
        if vix:
            vix_level = vix.get("current_price", 0)
            vix_high = thresholds["vix_high"]
            vix_low = thresholds["vix_low"]
            if vix_level > vix_high:
                parts.append(
                    f"VIX elevated at {vix_level:.1f}, above the {vix_high} threshold "
                    f"typical for {regime.value.replace('_', ' ')} regimes — hedging demand is rising"
                )
            elif vix_level < vix_low:
                parts.append(
                    f"VIX compressed at {vix_level:.1f}, below {vix_low} — "
                    f"complacency risk is elevated given current regime"
                )

        # Sector rotation vs regime expectations
        if sectors and level >= ReportLevel.STANDARD:
            sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
            leaders = [s[0] for s in sorted_sectors[:3]]
            laggards = [s[0] for s in sorted_sectors[-2:]]

            expected = _REGIME_SECTOR_LEADERS.get(regime, [])
            aligned = [s for s in leaders if s in expected]

            parts.append(
                f"Sector leaders: {', '.join(s.replace('_', ' ').title() for s in leaders)}. "
                f"Laggards: {', '.join(s.replace('_', ' ').title() for s in laggards)}"
            )

            if aligned:
                parts.append(
                    f"Rotation consistent with {regime.value.replace('_', ' ')} playbook "
                    f"({', '.join(s.replace('_', ' ').title() for s in aligned)} leading as expected)"
                )
            elif expected:
                parts.append(
                    f"Sector leadership diverges from regime expectation — "
                    f"{regime.value.replace('_', ' ')} typically favors "
                    f"{', '.join(s.replace('_', ' ').title() for s in expected[:2])}"
                )

        return ". ".join(parts) + "." if parts else "Equity markets trading mixed."

    # ── Fixed Income ────────────────────────────────────────

    def _build_fixed_income(self, data, level, regime, impl) -> FixedIncomeData:
        rates = data.get("rates", {})
        yield_curve = data.get("yield_curve", {})
        credit = data.get("credit", {})

        t10y = rates.get("treasury_10y", {}).get("latest_value", 0) if rates.get("treasury_10y") else 0
        spread_2s10s = yield_curve.get("spread_2s10s", 0)

        if spread_2s10s and spread_2s10s < 0:
            curve_shape = "inverted"
        elif spread_2s10s and spread_2s10s < 0.5:
            curve_shape = "flat"
        else:
            curve_shape = "normal"

        fi_bias = impl.get("fixed_income", {}).get("bias", "neutral")
        headline = f"10Y at {t10y:.2f}%, curve {curve_shape} — regime bias: {fi_bias}"

        commentary = self._fi_commentary(rates, yield_curve, credit, level, regime, impl)

        return FixedIncomeData(
            asset_class="fixed_income",
            headline=headline,
            data=data,
            commentary=commentary,
            yield_curve=yield_curve,
            credit_spreads=credit,
            curve_shape=curve_shape,
        )

    def _fi_commentary(self, rates, curve, credit, level, regime, impl) -> str:
        parts = []

        spread = curve.get("spread_2s10s")
        duration_rec = impl.get("fixed_income", {}).get("duration", "moderate")

        if spread is not None:
            if spread < 0:
                parts.append(
                    f"Yield curve inverted at {spread:.0f}bps. "
                    f"Historically a recession leading indicator, though timing is unreliable — "
                    f"current {regime.value.replace('_', ' ')} conditions suggest "
                    f"{'imminent stress' if regime in (MarketRegime.STAGFLATION, MarketRegime.RISK_OFF) else 'the signal may be premature'}"
                )
            elif spread < 50:
                parts.append(f"Curve flat at {spread:.0f}bps — late-cycle dynamics, duration recommendation: {duration_rec}")
            else:
                parts.append(f"Curve shape healthy at {spread:.0f}bps — consistent with {regime.value.replace('_', ' ')} regime")

        if credit and level >= ReportLevel.STANDARD:
            hy = credit.get("hy_spread", {}).get("latest_value")
            if hy:
                if hy > 500:
                    parts.append(f"HY spreads wide at {hy:.0f}bps — credit stress elevated, favoring up-in-quality")
                elif hy < 300:
                    credit_note = impl.get("fixed_income", {}).get("credit", "")
                    if credit_note == "favorable":
                        parts.append(f"HY spreads tight at {hy:.0f}bps — regime supports carry, but tightness limits further compression")
                    else:
                        parts.append(f"HY spreads tight at {hy:.0f}bps — risk appetite strong, but limited margin of safety")

        return ". ".join(parts) + "." if parts else "Fixed income markets stable."

    # ── FX ──────────────────────────────────────────────────

    def _build_fx(self, data, level, regime, thresholds, impl) -> FXData:
        dxy = data.get("dxy")
        pairs = data.get("pairs", {})

        dm_pairs = {k: v for k, v in pairs.items() if k in ["eurusd", "usdjpy", "gbpusd", "usdchf", "audusd"]}
        em_pairs = {k: v for k, v in pairs.items() if k in ["usdcnh", "usdmxn", "usdbrl"]}

        usd_strength = data.get("usd_strength_index", 0)
        if usd_strength > 0.5:
            usd_bias = "bullish"
        elif usd_strength < -0.5:
            usd_bias = "bearish"
        else:
            usd_bias = "neutral"

        fx_impl = impl.get("fx", {}).get("bias", "neutral")
        dxy_val = dxy.get("value", 0) if dxy else 0
        headline = f"DXY at {dxy_val:.2f}, USD {usd_bias} — regime expectation: {fx_impl}"

        commentary = self._fx_commentary(dxy, pairs, level, regime, thresholds, impl)

        return FXData(
            asset_class="fx",
            headline=headline,
            data=data,
            commentary=commentary,
            dxy=dxy,
            dm_pairs=dm_pairs,
            em_pairs=em_pairs,
            usd_bias=usd_bias,
        )

    def _fx_commentary(self, dxy, pairs, level, regime, thresholds, impl) -> str:
        parts = []
        fx_thresh = thresholds["fx"]

        if dxy:
            change = dxy.get("change_percent", 0)
            if abs(change) > fx_thresh:
                direction = "strengthening" if change > 0 else "weakening"
                parts.append(f"Dollar {direction} ({change:+.2f}%)")

                # Cross-reference with regime
                expected_bias = impl.get("fx", {}).get("bias", "neutral")
                if expected_bias == "usd_bullish" and change > 0:
                    parts.append("USD strength consistent with regime expectations")
                elif expected_bias == "safe_haven" and change > 0:
                    parts.append("Dollar bid aligns with safe-haven demand in current environment")
                elif expected_bias in ("usd_bullish", "safe_haven") and change < 0:
                    parts.append("Dollar weakness diverges from regime expectations — worth monitoring for regime shift signal")

        if "usdjpy" in pairs and level >= ReportLevel.STANDARD:
            jpy = pairs["usdjpy"]
            rate = jpy.get("rate", 0)
            if rate > 155:
                parts.append(f"USD/JPY at {rate:.1f} — deep intervention territory, positioning risk is asymmetric to the downside")
            elif rate > 150:
                parts.append(f"USD/JPY elevated at {rate:.1f} — BoJ verbal intervention likely, watch for tone shifts")

        if "eurusd" in pairs and level >= ReportLevel.STANDARD:
            eur = pairs["eurusd"]
            eur_change = eur.get("change_percent", 0)
            if abs(eur_change) > fx_thresh:
                direction = "firming" if eur_change > 0 else "softening"
                parts.append(f"EUR {direction} ({eur_change:+.2f}%) — reflects ECB vs Fed policy differential")

        return ". ".join(parts) + "." if parts else "FX markets trading rangebound."

    # ── Commodities ─────────────────────────────────────────

    def _build_commodities(self, data, level, regime, thresholds, impl) -> CommodityData:
        precious = data.get("precious_metals", {})
        energy = data.get("energy", {})
        agriculture = data.get("agriculture", {})

        gold = precious.get("gold", {})
        wti = energy.get("wti_crude", {})
        gold_price = gold.get("price", 0) if gold else 0
        wti_price = wti.get("price", 0) if wti else 0

        comm_bias = impl.get("commodities", {}).get("bias", "neutral")
        headline = f"Gold ${gold_price:,.0f}, WTI ${wti_price:.1f} — regime bias: {comm_bias}"

        commentary = self._commodity_commentary(precious, energy, level, regime, thresholds, impl)

        return CommodityData(
            asset_class="commodities",
            headline=headline,
            data=data,
            commentary=commentary,
            precious=precious,
            energy=energy,
            agriculture=agriculture if level >= ReportLevel.STANDARD else None,
        )

    def _commodity_commentary(self, precious, energy, level, regime, thresholds, impl) -> str:
        parts = []
        gold_thresh = thresholds["gold"]
        oil_thresh = thresholds["oil"]

        gold = precious.get("gold", {})
        wti = energy.get("wti_crude", {})

        if gold:
            change = gold.get("change_percent", 0)
            if abs(change) > gold_thresh:
                direction = "bid" if change > 0 else "offered"
                parts.append(f"Gold {direction} ({change:+.2f}%)")

                # Cross-reference with regime
                gold_focus = impl.get("commodities", {}).get("focus", [])
                if "gold" in gold_focus and change > 0:
                    parts.append(f"Gold strength aligns with {regime.value.replace('_', ' ')} regime playbook — real asset demand intact")
                elif "gold" in gold_focus and change < 0:
                    parts.append("Gold weakness despite regime favoring precious metals — potential positioning unwind or dollar strength")

        if wti:
            change = wti.get("change_percent", 0)
            if abs(change) > oil_thresh:
                direction = "rallying" if change > 0 else "selling off"
                parts.append(f"WTI {direction} ({change:+.2f}%)")

                if regime == MarketRegime.INFLATIONARY_EXPANSION and change > 0:
                    parts.append("Rising energy prices reinforce inflationary dynamics — watch for demand destruction threshold")
                elif regime == MarketRegime.RISK_OFF and change < 0:
                    parts.append("Oil weakness reflects growth concern — demand destruction expectations building")

        # Gold-oil ratio insight for L2+
        if gold and wti and level >= ReportLevel.STANDARD:
            gold_price = gold.get("price", 0)
            wti_price = wti.get("price", 0)
            if wti_price > 0 and gold_price > 0:
                ratio = gold_price / wti_price
                if ratio > 35:
                    parts.append(f"Gold/oil ratio elevated at {ratio:.1f} — market pricing recession risk over inflation")
                elif ratio < 20:
                    parts.append(f"Gold/oil ratio compressed at {ratio:.1f} — inflation and growth expectations both elevated")

        return ". ".join(parts) + "." if parts else "Commodities trading mixed."

    # ── Crypto ──────────────────────────────────────────────

    def _build_crypto(self, data, level, regime, thresholds, impl) -> CryptoData:
        assets = data.get("assets", {})
        overview = data.get("market_overview")
        fear_greed = data.get("fear_greed")

        btc = assets.get("bitcoin", {})
        eth = assets.get("ethereum", {})
        btc_price = btc.get("current_price", 0) if btc else 0
        eth_price = eth.get("current_price", 0) if eth else 0

        crypto_bias = impl.get("crypto", {}).get("bias", "neutral")
        headline = f"BTC ${btc_price:,.0f}, ETH ${eth_price:,.0f} — regime bias: {crypto_bias}"

        commentary = self._crypto_commentary(assets, fear_greed, level, regime, thresholds, impl)

        return CryptoData(
            asset_class="crypto",
            headline=headline,
            data=data,
            commentary=commentary,
            major_coins=assets,
            market_overview=overview,
            fear_greed=fear_greed,
        )

    def _crypto_commentary(self, assets, fear_greed, level, regime, thresholds, impl) -> str:
        parts = []
        btc_thresh = thresholds["btc"]

        btc = assets.get("bitcoin", {})
        eth = assets.get("ethereum", {})

        if btc:
            change = btc.get("price_change_percentage_24h", 0)
            if abs(change) > btc_thresh:
                direction = "surging" if change > 0 else "selling off"
                parts.append(f"Bitcoin {direction} ({change:+.1f}%)")
            else:
                parts.append(f"Bitcoin consolidating ({change:+.1f}%)")

            # BTC vs ETH divergence
            if eth:
                eth_change = eth.get("price_change_percentage_24h", 0)
                spread = eth_change - change
                if spread > 3:
                    parts.append("ETH outperforming BTC — risk appetite favoring higher-beta crypto, altcoin rotation underway")
                elif spread < -3:
                    parts.append("BTC outperforming ETH — flight-to-quality within crypto, defensive positioning")

        if fear_greed and level >= ReportLevel.STANDARD:
            classification = fear_greed.get("classification", "")
            value = fear_greed.get("value", 50)
            parts.append(f"Crypto Fear & Greed at {value:.0f}/100 ({classification})")

            crypto_bias = impl.get("crypto", {}).get("bias", "neutral")
            if value > 75 and crypto_bias == "bearish":
                parts.append("Extreme greed amid bearish regime — contrarian caution warranted")
            elif value < 25 and crypto_bias == "bullish":
                parts.append("Extreme fear with bullish regime backdrop — potential accumulation opportunity")

        return ". ".join(parts) + "." if parts else "Crypto markets consolidating."
