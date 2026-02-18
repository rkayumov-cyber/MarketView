"""Market Data Explorer page."""

import asyncio
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Market Data - MarketView",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Market Data Explorer")
st.markdown("Real-time market data across all asset classes")

# Tabs for different asset classes
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏛️ Equities", "💵 Fixed Income", "💱 FX", "🪙 Commodities", "₿ Crypto"
])

with tab1:
    st.subheader("Equity Markets")

    # US Indices
    st.markdown("### US Indices")
    us_col1, us_col2, us_col3, us_col4 = st.columns(4)

    with us_col1:
        st.metric("S&P 500", "5,234.56", "+23.45 (+0.45%)")
    with us_col2:
        st.metric("Nasdaq", "16,432.12", "+156.78 (+0.96%)")
    with us_col3:
        st.metric("Dow Jones", "39,456.78", "+145.23 (+0.37%)")
    with us_col4:
        st.metric("Russell 2000", "2,045.67", "-12.34 (-0.60%)")

    st.markdown("---")

    # Global Indices
    st.markdown("### Global Indices")
    global_col1, global_col2, global_col3, global_col4 = st.columns(4)

    with global_col1:
        st.metric("Nikkei 225", "38,234.56", "+234.56 (+0.62%)")
    with global_col2:
        st.metric("Euro Stoxx 50", "4,987.23", "+12.34 (+0.25%)")
    with global_col3:
        st.metric("FTSE 100", "7,654.32", "-23.45 (-0.31%)")
    with global_col4:
        st.metric("Hang Seng", "17,234.56", "+145.67 (+0.85%)")

    st.markdown("---")

    # Sector Performance
    st.markdown("### Sector Performance")

    sector_data = {
        "Sector": ["Technology", "Healthcare", "Financials", "Energy", "Materials",
                   "Industrials", "Consumer Disc.", "Consumer Staples", "Utilities", "Real Estate"],
        "Performance": [1.2, 0.5, -0.3, 2.1, 0.8, 0.4, -0.2, 0.1, -0.5, -0.8],
    }
    df_sectors = pd.DataFrame(sector_data)

    fig = px.bar(
        df_sectors,
        x="Sector",
        y="Performance",
        color="Performance",
        color_continuous_scale=["#e74c3c", "#f39c12", "#27ae60"],
        title="Sector Performance (%)",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Fixed Income")

    # Yield Curve
    st.markdown("### US Treasury Yield Curve")

    yield_data = {
        "Tenor": ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"],
        "Yield": [5.35, 5.40, 5.30, 4.95, 4.65, 4.35, 4.25, 4.45],
    }
    df_yields = pd.DataFrame(yield_data)

    fig_yield = px.line(
        df_yields,
        x="Tenor",
        y="Yield",
        markers=True,
        title="Treasury Yield Curve",
    )
    fig_yield.update_traces(line=dict(color="#4a90d9", width=3))
    st.plotly_chart(fig_yield, use_container_width=True)

    # Key Rates
    rate_col1, rate_col2, rate_col3, rate_col4 = st.columns(4)

    with rate_col1:
        st.metric("Fed Funds", "5.25-5.50%", "0.00%")
    with rate_col2:
        st.metric("2Y Treasury", "4.65%", "+0.02%")
    with rate_col3:
        st.metric("10Y Treasury", "4.25%", "+0.03%")
    with rate_col4:
        st.metric("2s10s Spread", "-40bps", "-2bps", delta_color="inverse")

    st.markdown("---")

    # Credit Spreads
    st.markdown("### Credit Spreads")
    credit_col1, credit_col2 = st.columns(2)

    with credit_col1:
        st.metric("Investment Grade", "98bps", "+2bps")
    with credit_col2:
        st.metric("High Yield", "345bps", "+5bps")

with tab3:
    st.subheader("Foreign Exchange")

    # DXY
    st.markdown("### Dollar Index (DXY)")
    st.metric("DXY", "104.25", "+0.15 (+0.14%)")

    st.markdown("---")

    # Major Pairs
    st.markdown("### Major Currency Pairs")

    fx_col1, fx_col2, fx_col3 = st.columns(3)

    with fx_col1:
        st.metric("EUR/USD", "1.0856", "-0.0012 (-0.11%)")
        st.metric("USD/JPY", "151.23", "+0.45 (+0.30%)")
    with fx_col2:
        st.metric("GBP/USD", "1.2678", "+0.0023 (+0.18%)")
        st.metric("USD/CHF", "0.8912", "+0.0008 (+0.09%)")
    with fx_col3:
        st.metric("AUD/USD", "0.6545", "-0.0015 (-0.23%)")
        st.metric("USD/CAD", "1.3678", "+0.0012 (+0.09%)")

    st.markdown("---")

    # EM Currencies
    st.markdown("### Emerging Market Currencies")
    em_col1, em_col2, em_col3 = st.columns(3)

    with em_col1:
        st.metric("USD/CNH", "7.2456", "+0.0123 (+0.17%)")
    with em_col2:
        st.metric("USD/MXN", "17.15", "-0.08 (-0.47%)")
    with em_col3:
        st.metric("USD/BRL", "5.02", "+0.03 (+0.60%)")

with tab4:
    st.subheader("Commodities")

    # Precious Metals
    st.markdown("### Precious Metals")
    pm_col1, pm_col2 = st.columns(2)

    with pm_col1:
        st.metric("Gold", "$2,345.67", "+$12.34 (+0.53%)")
    with pm_col2:
        st.metric("Silver", "$27.89", "+$0.45 (+1.64%)")

    st.markdown("---")

    # Energy
    st.markdown("### Energy")
    energy_col1, energy_col2, energy_col3 = st.columns(3)

    with energy_col1:
        st.metric("WTI Crude", "$78.45", "+$1.23 (+1.59%)")
    with energy_col2:
        st.metric("Brent Crude", "$82.34", "+$1.12 (+1.38%)")
    with energy_col3:
        st.metric("Natural Gas", "$2.45", "-$0.08 (-3.16%)")

    st.markdown("---")

    # Agriculture
    st.markdown("### Agriculture")
    ag_col1, ag_col2, ag_col3 = st.columns(3)

    with ag_col1:
        st.metric("Corn", "$4.56", "-$0.02 (-0.44%)")
    with ag_col2:
        st.metric("Wheat", "$5.78", "+$0.12 (+2.12%)")
    with ag_col3:
        st.metric("Soybeans", "$11.23", "+$0.08 (+0.72%)")

with tab5:
    st.subheader("Cryptocurrency")

    # Major Coins
    st.markdown("### Major Cryptocurrencies")

    crypto_col1, crypto_col2, crypto_col3 = st.columns(3)

    with crypto_col1:
        st.metric("Bitcoin", "$67,432", "+$1,234 (+1.86%)")
        st.metric("Solana", "$145.67", "+$5.23 (+3.72%)")
    with crypto_col2:
        st.metric("Ethereum", "$3,456", "+$78 (+2.31%)")
        st.metric("XRP", "$0.52", "+$0.02 (+4.00%)")
    with crypto_col3:
        st.metric("BNB", "$567.89", "+$12.34 (+2.22%)")
        st.metric("Cardano", "$0.45", "+$0.01 (+2.27%)")

    st.markdown("---")

    # Market Overview
    st.markdown("### Market Overview")
    market_col1, market_col2, market_col3, market_col4 = st.columns(4)

    with market_col1:
        st.metric("Total Market Cap", "$2.45T", "+$45B (+1.87%)")
    with market_col2:
        st.metric("BTC Dominance", "52.3%", "+0.5%")
    with market_col3:
        st.metric("Fear & Greed", "65", "Greed")
    with market_col4:
        st.metric("24h Volume", "$78.5B", "+$5.2B")

    st.markdown("---")

    # Fear & Greed Gauge
    st.markdown("### Market Sentiment")

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=65,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Crypto Fear & Greed Index"},
        gauge={
            "axis": {"range": [None, 100]},
            "bar": {"color": "#f39c12"},
            "steps": [
                {"range": [0, 25], "color": "#e74c3c"},
                {"range": [25, 45], "color": "#f39c12"},
                {"range": [45, 55], "color": "#95a5a6"},
                {"range": [55, 75], "color": "#27ae60"},
                {"range": [75, 100], "color": "#2ecc71"},
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": 65,
            },
        },
    ))

    st.plotly_chart(fig_gauge, use_container_width=True)

# Refresh button
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.rerun()

st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
