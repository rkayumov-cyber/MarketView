"""Step 1: Market Data Explorer — fetch real data from backend API."""

from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Market Data - MarketView", page_icon="📈", layout="wide")

from dashboard.workflow_state import (
    WORKFLOW_CSS,
    init_session_state,
    mark_step_complete,
    render_sidebar,
    render_workflow_steps,
)
from dashboard import api_client

init_session_state()
st.markdown(WORKFLOW_CSS, unsafe_allow_html=True)
render_sidebar()

# ── Header ──────────────────────────────────────────────────

st.title("Step 1: Market Data Explorer")
render_workflow_steps(current_step=1)
st.markdown("")

# ── Load Data ───────────────────────────────────────────────

source_label = st.session_state.get("data_source", "live")
st.caption(f"Data source: **{source_label}**")

if st.button("Load All Market Data", type="primary", use_container_width=True):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    endpoints = [
        ("Snapshot", api_client.fetch_snapshot, "market_snapshot"),
        ("Equities", api_client.fetch_equities, "market_equities"),
        ("FX", api_client.fetch_fx, "market_fx"),
        ("Commodities", api_client.fetch_commodities, "market_commodities"),
        ("Crypto", api_client.fetch_crypto, "market_crypto"),
    ]

    progress = st.progress(0)
    status = st.empty()
    status.text("Fetching all market data in parallel...")

    results: dict[str, dict | None] = {}
    with ThreadPoolExecutor(max_workers=len(endpoints)) as pool:
        futures = {pool.submit(fn): (label, key) for label, fn, key in endpoints}
        done_count = 0
        for future in as_completed(futures):
            label, key = futures[future]
            results[key] = future.result()
            done_count += 1
            progress.progress(done_count / len(endpoints))

    for key, result in results.items():
        if result:
            st.session_state[key] = result

    status.empty()
    st.session_state["market_data_timestamp"] = datetime.utcnow().isoformat()[:19]
    mark_step_complete("market_data")
    st.success("All market data loaded!")
    st.rerun()

# ── Check if data loaded ───────────────────────────────────

has_data = st.session_state.get("market_equities") is not None

if not has_data:
    st.info("Click **Load All Market Data** above to fetch live data from the backend.")
    st.stop()

ts = st.session_state.get("market_data_timestamp", "")
if ts:
    st.caption(f"Last loaded: {ts}")

st.markdown("---")

# ── Tabs ────────────────────────────────────────────────────

tab_eq, tab_fx, tab_comm, tab_crypto = st.tabs(
    ["Equities", "FX", "Commodities", "Crypto"]
)


# ── Helper ──────────────────────────────────────────────────

def _fmt_price(val, prefix="", decimals=2):
    if val is None:
        return "N/A"
    return f"{prefix}{val:,.{decimals}f}"


def _fmt_change(change, change_pct):
    if change is None:
        return "N/A"
    sign = "+" if change >= 0 else ""
    pct_str = f" ({sign}{change_pct:.2f}%)" if change_pct is not None else ""
    return f"{sign}{change:,.2f}{pct_str}"


# ── Equities Tab ────────────────────────────────────────────

with tab_eq:
    eq_data = st.session_state["market_equities"].get("data", {})
    eq_source = st.session_state["market_equities"].get("source", "")
    st.caption(f"Source: {eq_source}")

    # US Indices
    st.markdown("### US Indices")
    us = eq_data.get("us", {})
    us_cols = st.columns(4)

    for i, (key, label) in enumerate([
        ("spx", "S&P 500"), ("nasdaq", "NASDAQ"), ("dow", "Dow Jones"), ("russell2000", "Russell 2000"),
    ]):
        idx = us.get(key, {})
        with us_cols[i]:
            st.metric(
                label,
                _fmt_price(idx.get("current_price")),
                _fmt_change(idx.get("change"), idx.get("change_percent")),
            )

    st.markdown("---")

    # Global Indices
    st.markdown("### Global Indices")
    gl = eq_data.get("global", {})
    global_indices = [
        ("nikkei", "Nikkei 225"),
        ("eurostoxx50", "Euro Stoxx 50"),
        ("ftse100", "FTSE 100"),
        ("dax", "DAX"),
        ("hang_seng", "Hang Seng"),
        ("shanghai", "SSE Composite"),
        ("nifty50", "NIFTY 50"),
    ]

    row1 = st.columns(4)
    row2 = st.columns(4)
    all_cols = row1 + row2

    for i, (key, label) in enumerate(global_indices):
        idx = gl.get(key, {})
        with all_cols[i]:
            st.metric(
                label,
                _fmt_price(idx.get("current_price")),
                _fmt_change(idx.get("change"), idx.get("change_percent")),
            )

    st.markdown("---")

    # Sector Performance
    st.markdown("### Sector Performance")
    sectors = eq_data.get("sectors", {})
    if sectors:
        sector_names = [s.replace("_", " ").title() for s in sectors.keys()]
        sector_values = list(sectors.values())
        df_sectors = pd.DataFrame({"Sector": sector_names, "Performance (%)": sector_values})

        fig = px.bar(
            df_sectors, x="Sector", y="Performance (%)",
            color="Performance (%)",
            color_continuous_scale=["#e74c3c", "#f39c12", "#27ae60"],
            title="Sector Performance (%)",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # VIX
    vix = eq_data.get("vix", {})
    if vix:
        st.markdown("### Volatility")
        vix_cols = st.columns(4)
        with vix_cols[0]:
            st.metric("VIX", _fmt_price(vix.get("current_price")),
                       _fmt_change(vix.get("change"), vix.get("change_percent")),
                       delta_color="inverse")
        with vix_cols[1]:
            st.metric("52W High", _fmt_price(vix.get("fifty_two_week_high")))
        with vix_cols[2]:
            st.metric("52W Low", _fmt_price(vix.get("fifty_two_week_low")))


# ── FX Tab ──────────────────────────────────────────────────

with tab_fx:
    fx_data = st.session_state["market_fx"].get("data", {})
    fx_source = st.session_state["market_fx"].get("source", "")
    st.caption(f"Source: {fx_source}")

    # DXY
    dxy = fx_data.get("dxy", {})
    st.markdown("### Dollar Index (DXY)")
    dxy_cols = st.columns(4)
    with dxy_cols[0]:
        st.metric("DXY", _fmt_price(dxy.get("value")),
                   _fmt_change(dxy.get("change"), dxy.get("change_percent")))
    with dxy_cols[1]:
        st.metric("Day High", _fmt_price(dxy.get("day_high")))
    with dxy_cols[2]:
        st.metric("Day Low", _fmt_price(dxy.get("day_low")))

    st.markdown("---")

    # Currency pairs
    pairs = fx_data.get("pairs", {})
    major_keys = ["eurusd", "usdjpy", "gbpusd", "usdchf", "audusd", "usdcad"]
    em_keys = ["usdcnh", "usdmxn", "usdbrl"]

    st.markdown("### Major Pairs")
    major_cols = st.columns(3)
    for i, key in enumerate(major_keys):
        pair = pairs.get(key, {})
        with major_cols[i % 3]:
            st.metric(
                pair.get("pair", key.upper()),
                _fmt_price(pair.get("rate"), decimals=4),
                _fmt_change(pair.get("change"), pair.get("change_percent")),
            )

    st.markdown("---")

    st.markdown("### Emerging Market Currencies")
    em_cols = st.columns(3)
    for i, key in enumerate(em_keys):
        pair = pairs.get(key, {})
        with em_cols[i]:
            st.metric(
                pair.get("pair", key.upper()),
                _fmt_price(pair.get("rate"), decimals=4 if pair.get("rate", 0) < 10 else 2),
                _fmt_change(pair.get("change"), pair.get("change_percent")),
            )


# ── Commodities Tab ─────────────────────────────────────────

with tab_comm:
    comm_data = st.session_state["market_commodities"].get("data", {})
    comm_source = st.session_state["market_commodities"].get("source", "")
    st.caption(f"Source: {comm_source}")

    # Precious Metals
    st.markdown("### Precious Metals")
    metals = comm_data.get("precious_metals", {})
    metal_cols = st.columns(2)
    for i, (key, label) in enumerate([("gold", "Gold"), ("silver", "Silver")]):
        m = metals.get(key, {})
        with metal_cols[i]:
            st.metric(label, _fmt_price(m.get("price"), "$"),
                       _fmt_change(m.get("change"), m.get("change_percent")))

    st.markdown("---")

    # Energy
    st.markdown("### Energy")
    energy = comm_data.get("energy", {})
    energy_cols = st.columns(3)
    for i, (key, label) in enumerate([
        ("wti_crude", "WTI Crude"), ("brent_crude", "Brent Crude"), ("natural_gas", "Natural Gas"),
    ]):
        e = energy.get(key, {})
        with energy_cols[i]:
            st.metric(label, _fmt_price(e.get("price"), "$"),
                       _fmt_change(e.get("change"), e.get("change_percent")))

    st.markdown("---")

    # Agriculture
    st.markdown("### Agriculture")
    ag = comm_data.get("agriculture", {})
    ag_cols = st.columns(3)
    for i, (key, label) in enumerate([("corn", "Corn"), ("wheat", "Wheat"), ("soybeans", "Soybeans")]):
        a = ag.get(key, {})
        with ag_cols[i]:
            st.metric(label, _fmt_price(a.get("price"), "$"),
                       _fmt_change(a.get("change"), a.get("change_percent")))

    # Industrial
    industrial = comm_data.get("industrial", {})
    if industrial:
        st.markdown("---")
        st.markdown("### Industrial Metals")
        ind_cols = st.columns(3)
        for i, (key, m) in enumerate(industrial.items()):
            with ind_cols[i % 3]:
                st.metric(m.get("name", key), _fmt_price(m.get("price"), "$"),
                           _fmt_change(m.get("change"), m.get("change_percent")))


# ── Crypto Tab ──────────────────────────────────────────────

with tab_crypto:
    crypto_data = st.session_state["market_crypto"].get("data", {})
    crypto_source = st.session_state["market_crypto"].get("source", "")
    st.caption(f"Source: {crypto_source}")

    # Coins
    st.markdown("### Major Cryptocurrencies")
    assets = crypto_data.get("assets", {})

    crypto_cols = st.columns(3)
    for i, (key, coin) in enumerate(assets.items()):
        with crypto_cols[i % 3]:
            price = coin.get("current_price", 0)
            prefix = "$"
            decimals = 2 if price >= 1 else 4
            st.metric(
                f"{coin.get('name', key)} ({coin.get('symbol', '')})",
                _fmt_price(price, prefix, decimals),
                f"{coin.get('price_change_percentage_24h', 0):+.2f}% (24h)",
            )

    st.markdown("---")

    # Market Overview
    st.markdown("### Market Overview")
    overview = crypto_data.get("market_overview", {})
    if overview:
        ov_cols = st.columns(4)
        with ov_cols[0]:
            mcap = overview.get("total_market_cap", 0)
            st.metric("Total Market Cap", f"${mcap / 1e12:.2f}T")
        with ov_cols[1]:
            st.metric("BTC Dominance", f"{overview.get('btc_dominance', 0):.1f}%")
        with ov_cols[2]:
            vol = overview.get("total_volume", 0)
            st.metric("24h Volume", f"${vol / 1e9:.1f}B")
        with ov_cols[3]:
            st.metric("24h Change", f"{overview.get('market_cap_change_24h', 0):+.2f}%")

    st.markdown("---")

    # Fear & Greed
    st.markdown("### Market Sentiment")
    fg = crypto_data.get("fear_greed", {})
    if fg:
        fg_value = fg.get("value", 50)
        fg_label = fg.get("classification", "Neutral")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fg_value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": f"Crypto Fear & Greed Index — {fg_label}"},
            gauge={
                "axis": {"range": [0, 100]},
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
                    "value": fg_value,
                },
            },
        ))
        fig_gauge.update_layout(height=350)
        st.plotly_chart(fig_gauge, use_container_width=True)

# ── Navigation ──────────────────────────────────────────────

st.markdown("---")
nav_cols = st.columns([1, 1])
with nav_cols[1]:
    if st.button("Continue to Step 2: Research Sources >>", use_container_width=True, type="primary"):
        st.switch_page("pages/2_Research_Sources.py")
