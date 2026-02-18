"""Main Streamlit application for MarketView Dashboard."""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="MarketView - Daily Alpha Brief",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a1a2e;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .bullish { color: #27ae60; }
    .bearish { color: #e74c3c; }
    .neutral { color: #f39c12; }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #4a90d9;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("📊 MarketView")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "📈 Market Data", "📝 Generate Report", "⚙️ Settings"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.info(
    "MarketView generates institutional-grade market analysis reports. "
    "Select 'Generate Report' to create your Daily Alpha Brief."
)

# Main content based on selection
if page == "🏠 Dashboard":
    st.markdown('<p class="main-header">📊 MarketView Dashboard</p>', unsafe_allow_html=True)
    st.markdown("Welcome to MarketView - Your Institutional Market Analysis Platform")

    # Quick stats row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="S&P 500",
            value="5,234.56",
            delta="+0.45%",
        )

    with col2:
        st.metric(
            label="VIX",
            value="14.32",
            delta="-0.87",
            delta_color="inverse",
        )

    with col3:
        st.metric(
            label="10Y Treasury",
            value="4.25%",
            delta="+0.03%",
        )

    with col4:
        st.metric(
            label="Bitcoin",
            value="$67,432",
            delta="+2.3%",
        )

    st.markdown("---")

    # Market Regime
    st.markdown('<p class="section-header">Current Market Regime</p>', unsafe_allow_html=True)

    regime_col1, regime_col2 = st.columns([2, 1])

    with regime_col1:
        st.info(
            "**Goldilocks** - Markets in favorable environment with moderate growth, "
            "contained inflation, and supportive financial conditions."
        )

    with regime_col2:
        st.metric(label="Regime Confidence", value="78%")

    st.markdown("---")

    # Quick Links
    st.markdown('<p class="section-header">Quick Actions</p>', unsafe_allow_html=True)

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if st.button("📋 Generate Executive Brief", use_container_width=True):
            st.switch_page("pages/2_Generate_Report.py")

    with action_col2:
        if st.button("📊 View Market Data", use_container_width=True):
            st.switch_page("pages/1_Market_Data.py")

    with action_col3:
        if st.button("📁 View Past Reports", use_container_width=True):
            st.info("Report history coming soon!")

elif page == "📈 Market Data":
    st.markdown("Redirecting to Market Data page...")
    st.switch_page("pages/1_Market_Data.py")

elif page == "📝 Generate Report":
    st.markdown("Redirecting to Report Generation page...")
    st.switch_page("pages/2_Generate_Report.py")

elif page == "⚙️ Settings":
    st.markdown('<p class="main-header">⚙️ Settings</p>', unsafe_allow_html=True)

    st.subheader("API Configuration")

    with st.form("api_settings"):
        fred_key = st.text_input("FRED API Key", type="password")
        reddit_id = st.text_input("Reddit Client ID", type="password")
        reddit_secret = st.text_input("Reddit Client Secret", type="password")

        st.markdown("---")

        st.subheader("Report Defaults")
        default_level = st.selectbox(
            "Default Report Level",
            options=["Executive", "Standard", "Deep Dive"],
            index=1,
        )

        default_format = st.selectbox(
            "Default Output Format",
            options=["Markdown", "PDF", "HTML"],
            index=0,
        )

        if st.form_submit_button("Save Settings"):
            st.success("Settings saved successfully!")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("MarketView v1.0.0")
st.sidebar.caption("© 2024 MarketView Team")
