"""
JSE Decision-Support System
A Streamlit in Snowflake application for JSE-listed equities analysis.
"""
import streamlit as st

# Note: st.set_page_config() is not supported in Streamlit in Snowflake
# Page configuration is managed by Snowflake

# Initialize all session state BEFORE navigation
# Company & Data State
st.session_state.setdefault("companies", [])  # User-added companies with sectors
st.session_state.setdefault("watchlist", [])
st.session_state.setdefault("selected_ticker", None)

# Document & Ingestion State
st.session_state.setdefault("uploaded_documents", [])
st.session_state.setdefault("ingested_sources", [])
st.session_state.setdefault("api_connections", {})

# Chat & AI State
st.session_state.setdefault("messages", [])
st.session_state.setdefault("chat_context", None)

# SENS & Alerts State
st.session_state.setdefault("sens_alerts", [])
st.session_state.setdefault("tracked_tickers", [])

# Settings State
st.session_state.setdefault("cortex_model", "claude-3-5-sonnet")
st.session_state.setdefault("temperature", 0.3)
st.session_state.setdefault("max_tokens", 2048)

# Define pages with Material icons
page_dashboard = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
    icon=":material/dashboard:"
)
page_research = st.Page(
    "pages/company_research.py",
    title="Company Research",
    icon=":material/analytics:"
)
page_ingestion = st.Page(
    "pages/data_ingestion.py",
    title="Data Ingestion",
    icon=":material/upload_file:"
)
page_analyst = st.Page(
    "pages/ai_analyst.py",
    title="AI Analyst",
    icon=":material/psychology:"
)
page_sens = st.Page(
    "pages/sens_monitor.py",
    title="SENS Monitor",
    icon=":material/notifications:"
)
page_settings = st.Page(
    "pages/settings.py",
    title="Settings",
    icon=":material/settings:"
)

# Navigation with top position for horizontal nav bar
pg = st.navigation(
    {
        "": [page_dashboard, page_research, page_analyst],
        "Data": [page_ingestion, page_sens],
        "Config": [page_settings],
    },
    position="top"
)

pg.run()
