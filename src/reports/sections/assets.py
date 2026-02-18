"""Asset section builder."""

from src.ingestion.aggregator import DataAggregator
from src.reports.models import (
    AssetSection,
    EquityData,
    FixedIncomeData,
    FXData,
    CommodityData,
    CryptoData,
    ReportLevel,
)


class AssetSectionBuilder:
    """Builder for the Asset class deep dive section."""

    def __init__(self) -> None:
        self.aggregator = DataAggregator()

    async def build(self, level: ReportLevel) -> AssetSection:
        """Build the Asset section."""
        # Get full market snapshot
        snapshot = await self.aggregator.get_full_snapshot()

        # Build each asset class section
        equities = self._build_equities(snapshot.equities, level)
        fixed_income = self._build_fixed_income(snapshot.fixed_income, level)
        fx = self._build_fx(snapshot.fx, level)
        commodities = self._build_commodities(snapshot.commodities, level)
        crypto = self._build_crypto(snapshot.crypto, level)

        return AssetSection(
            equities=equities,
            fixed_income=fixed_income,
            fx=fx,
            commodities=commodities,
            crypto=crypto,
        )

    def _build_equities(self, data: dict, level: ReportLevel) -> EquityData:
        """Build equity section."""
        us_indices = data.get("us", {})
        global_indices = data.get("global", {})
        sectors = data.get("sectors", {})
        vix = data.get("vix")

        # Generate headline
        spx = us_indices.get("spx", {})
        spx_change = spx.get("change_percent", 0) if spx else 0

        if spx_change > 1:
            headline = f"Risk-on day: S&P 500 up {spx_change:.1f}%"
        elif spx_change < -1:
            headline = f"Risk-off day: S&P 500 down {abs(spx_change):.1f}%"
        else:
            headline = f"Quiet session: S&P 500 {'+' if spx_change >= 0 else ''}{spx_change:.1f}%"

        # Generate commentary
        commentary = self._generate_equity_commentary(us_indices, sectors, vix, level)

        # Key levels
        key_levels = {}
        if spx:
            key_levels["SPX"] = spx.get("current_price", 0)
        if "nasdaq" in us_indices:
            key_levels["NDX"] = us_indices["nasdaq"].get("current_price", 0)

        return EquityData(
            asset_class="equity",
            headline=headline,
            data=data,
            key_levels=key_levels,
            commentary=commentary,
            us_indices=us_indices,
            global_indices=global_indices,
            sectors=sectors,
            vix=vix,
        )

    def _generate_equity_commentary(
        self, us: dict, sectors: dict, vix: dict, level: ReportLevel
    ) -> str:
        """Generate equity commentary."""
        parts = []

        # US performance
        if "spx" in us:
            spx = us["spx"]
            parts.append(
                f"S&P 500 at {spx.get('current_price', 0):,.0f} "
                f"({spx.get('change_percent', 0):+.1f}%)"
            )

        # VIX
        if vix:
            vix_level = vix.get("current_price", 0)
            if vix_level > 25:
                parts.append(f"VIX elevated at {vix_level:.1f}")
            elif vix_level < 15:
                parts.append(f"VIX complacent at {vix_level:.1f}")

        # Sector rotation
        if sectors and level >= ReportLevel.STANDARD:
            sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
            leaders = [s[0] for s in sorted_sectors[:2]]
            laggards = [s[0] for s in sorted_sectors[-2:]]
            parts.append(f"Leaders: {', '.join(leaders)}. Laggards: {', '.join(laggards)}")

        return ". ".join(parts) + "." if parts else "Equity markets trading mixed."

    def _build_fixed_income(self, data: dict, level: ReportLevel) -> FixedIncomeData:
        """Build fixed income section."""
        rates = data.get("rates", {})
        yield_curve = data.get("yield_curve", {})
        credit = data.get("credit", {})

        # Get key rates
        t10y = rates.get("treasury_10y", {}).get("latest_value", 0) if rates.get("treasury_10y") else 0
        spread_2s10s = yield_curve.get("spread_2s10s", 0)

        # Determine curve shape
        if spread_2s10s and spread_2s10s < 0:
            curve_shape = "inverted"
        elif spread_2s10s and spread_2s10s < 0.5:
            curve_shape = "flat"
        else:
            curve_shape = "normal"

        # Generate headline
        headline = f"10Y at {t10y:.2f}%, curve {curve_shape}"

        # Commentary
        commentary = self._generate_fi_commentary(rates, yield_curve, credit, level)

        return FixedIncomeData(
            asset_class="fixed_income",
            headline=headline,
            data=data,
            commentary=commentary,
            yield_curve=yield_curve,
            credit_spreads=credit,
            curve_shape=curve_shape,
        )

    def _generate_fi_commentary(
        self, rates: dict, curve: dict, credit: dict, level: ReportLevel
    ) -> str:
        """Generate fixed income commentary."""
        parts = []

        spread = curve.get("spread_2s10s")
        if spread is not None:
            if spread < 0:
                parts.append(f"Yield curve inverted at {spread:.0f}bps - recession signal")
            elif spread < 50:
                parts.append(f"Yield curve flat at {spread:.0f}bps - late cycle")

        if credit and level >= ReportLevel.STANDARD:
            hy = credit.get("hy_spread", {}).get("latest_value")
            if hy:
                if hy > 500:
                    parts.append(f"HY spreads wide at {hy:.0f}bps - stress elevated")
                elif hy < 300:
                    parts.append(f"HY spreads tight at {hy:.0f}bps - risk appetite strong")

        return ". ".join(parts) + "." if parts else "Fixed income markets stable."

    def _build_fx(self, data: dict, level: ReportLevel) -> FXData:
        """Build FX section."""
        dxy = data.get("dxy")
        pairs = data.get("pairs", {})

        # Split DM and EM
        dm_pairs = {k: v for k, v in pairs.items() if k in ["eurusd", "usdjpy", "gbpusd", "usdchf", "audusd"]}
        em_pairs = {k: v for k, v in pairs.items() if k in ["usdcnh", "usdmxn", "usdbrl"]}

        # Determine USD bias
        usd_strength = data.get("usd_strength_index", 0)
        if usd_strength > 0.5:
            usd_bias = "bullish"
        elif usd_strength < -0.5:
            usd_bias = "bearish"
        else:
            usd_bias = "neutral"

        # Generate headline
        dxy_val = dxy.get("value", 0) if dxy else 0
        headline = f"DXY at {dxy_val:.2f}, USD {usd_bias}"

        # Commentary
        commentary = self._generate_fx_commentary(dxy, pairs, level)

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

    def _generate_fx_commentary(self, dxy: dict, pairs: dict, level: ReportLevel) -> str:
        """Generate FX commentary."""
        parts = []

        if dxy:
            change = dxy.get("change_percent", 0)
            if abs(change) > 0.3:
                direction = "higher" if change > 0 else "lower"
                parts.append(f"Dollar trading {direction} ({change:+.1f}%)")

        if "usdjpy" in pairs and level >= ReportLevel.STANDARD:
            jpy = pairs["usdjpy"]
            rate = jpy.get("rate", 0)
            if rate > 150:
                parts.append(f"USD/JPY elevated at {rate:.1f} - BoJ intervention watch")

        return ". ".join(parts) + "." if parts else "FX markets trading rangebound."

    def _build_commodities(self, data: dict, level: ReportLevel) -> CommodityData:
        """Build commodities section."""
        precious = data.get("precious_metals", {})
        energy = data.get("energy", {})
        agriculture = data.get("agriculture", {})

        # Generate headline from gold and oil
        gold = precious.get("gold", {})
        wti = energy.get("wti_crude", {})

        gold_price = gold.get("price", 0) if gold else 0
        wti_price = wti.get("price", 0) if wti else 0

        headline = f"Gold ${gold_price:,.0f}, WTI ${wti_price:.1f}"

        # Commentary
        commentary = self._generate_commodity_commentary(precious, energy, level)

        return CommodityData(
            asset_class="commodities",
            headline=headline,
            data=data,
            commentary=commentary,
            precious=precious,
            energy=energy,
            agriculture=agriculture if level >= ReportLevel.STANDARD else None,
        )

    def _generate_commodity_commentary(
        self, precious: dict, energy: dict, level: ReportLevel
    ) -> str:
        """Generate commodity commentary."""
        parts = []

        gold = precious.get("gold", {})
        if gold:
            change = gold.get("change_percent", 0)
            if abs(change) > 0.5:
                direction = "bid" if change > 0 else "offered"
                parts.append(f"Gold {direction} ({change:+.1f}%)")

        wti = energy.get("wti_crude", {})
        if wti:
            change = wti.get("change_percent", 0)
            if abs(change) > 1:
                direction = "rallying" if change > 0 else "selling off"
                parts.append(f"WTI {direction} ({change:+.1f}%)")

        return ". ".join(parts) + "." if parts else "Commodities trading mixed."

    def _build_crypto(self, data: dict, level: ReportLevel) -> CryptoData:
        """Build crypto section."""
        assets = data.get("assets", {})
        overview = data.get("market_overview")
        fear_greed = data.get("fear_greed")

        # Get BTC and ETH
        btc = assets.get("bitcoin", {})
        eth = assets.get("ethereum", {})

        btc_price = btc.get("current_price", 0) if btc else 0
        eth_price = eth.get("current_price", 0) if eth else 0

        headline = f"BTC ${btc_price:,.0f}, ETH ${eth_price:,.0f}"

        # Commentary
        commentary = self._generate_crypto_commentary(assets, fear_greed, level)

        return CryptoData(
            asset_class="crypto",
            headline=headline,
            data=data,
            commentary=commentary,
            major_coins=assets,
            market_overview=overview,
            fear_greed=fear_greed,
        )

    def _generate_crypto_commentary(
        self, assets: dict, fear_greed: dict, level: ReportLevel
    ) -> str:
        """Generate crypto commentary."""
        parts = []

        btc = assets.get("bitcoin", {})
        if btc:
            change = btc.get("price_change_percentage_24h", 0)
            if abs(change) > 3:
                direction = "surging" if change > 0 else "dumping"
                parts.append(f"Bitcoin {direction} ({change:+.1f}%)")

        if fear_greed and level >= ReportLevel.STANDARD:
            classification = fear_greed.get("classification", "")
            value = fear_greed.get("value", 50)
            parts.append(f"Crypto sentiment: {classification} ({value:.0f}/100)")

        return ". ".join(parts) + "." if parts else "Crypto markets consolidating."
