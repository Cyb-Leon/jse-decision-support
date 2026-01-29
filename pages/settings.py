"""
Settings Page - Configuration and user preferences.
JSE Decision-Support System
"""
import streamlit as st
import json
from datetime import datetime

import sys
sys.path.append("..")
from utils.cortex_utils import CORTEX_MODELS
from utils.snowflake_utils import get_session, is_sis_environment


def render_model_settings():
    """Render AI model configuration."""
    st.subheader(":material/psychology: AI Model Settings")
    
    with st.container(border=True):
        # Model selection
        model_index = CORTEX_MODELS.index(st.session_state.cortex_model) if st.session_state.cortex_model in CORTEX_MODELS else 0
        
        new_model = st.selectbox(
            "Default Cortex Model",
            options=CORTEX_MODELS,
            index=model_index,
            help="Select the default LLM model for AI analysis",
            key="settings_model_select"
        )
        
        if new_model != st.session_state.cortex_model:
            st.session_state.cortex_model = new_model
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Temperature
            new_temp = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.temperature,
                step=0.1,
                help="Higher values make output more random, lower values more deterministic",
                key="settings_temp_slider"
            )
            if new_temp != st.session_state.temperature:
                st.session_state.temperature = new_temp
        
        with col2:
            # Max tokens
            new_tokens = st.number_input(
                "Max Tokens",
                min_value=256,
                max_value=4096,
                value=st.session_state.max_tokens,
                step=256,
                help="Maximum length of AI responses",
                key="settings_tokens_input"
            )
            if new_tokens != st.session_state.max_tokens:
                st.session_state.max_tokens = new_tokens
        
        st.caption(f"Current model: **{st.session_state.cortex_model}** | Temp: {st.session_state.temperature} | Max tokens: {st.session_state.max_tokens}")


def render_connection_settings():
    """Render Snowflake connection settings."""
    st.subheader(":material/database: Snowflake Connection")
    
    with st.container(border=True):
        # Check environment
        is_sis = is_sis_environment()
        
        if is_sis:
            st.success(":material/check_circle: Running in Streamlit in Snowflake")
            st.caption("Connection is managed automatically by Snowflake.")
            
            session = get_session()
            if session:
                st.caption(f"Session active: Yes")
        else:
            st.info(":material/info: Running in local/external environment")
            st.caption("Configure connection in `.streamlit/secrets.toml`")
            
            with st.expander(":material/code: secrets.toml template"):
                st.code("""
[connections.snowflake]
account = "your_account"
user = "your_user"
password = "your_password"
role = "your_role"
warehouse = "COMPUTE_WH"
database = "your_database"
schema = "your_schema"
                """, language="toml")
            
            session = get_session()
            if session:
                st.success(":material/check_circle: Connected to Snowflake")
            else:
                st.warning(":material/warning: Not connected")
        
        # Test connection button
        if st.button(":material/refresh: Test Connection", use_container_width=True):
            with st.spinner("Testing connection..."):
                session = get_session()
                if session:
                    try:
                        result = session.sql("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE()").collect()
                        st.success("Connection successful!")
                        st.caption(f"User: {result[0][0]} | Role: {result[0][1]} | Warehouse: {result[0][2]}")
                    except Exception as e:
                        st.error(f"Connection test failed: {e}")
                else:
                    st.error("No session available")


def render_data_settings():
    """Render data management settings."""
    st.subheader(":material/storage: Data Management")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Session Data**")
            st.caption(f"Documents: {len(st.session_state.uploaded_documents)}")
            st.caption(f"Portfolio holdings: {len(st.session_state.portfolio)}")
            st.caption(f"Watchlist: {len(st.session_state.watchlist)}")
            st.caption(f"Chat messages: {len(st.session_state.messages)}")
            st.caption(f"SENS alerts: {len(st.session_state.sens_alerts)}")
        
        with col2:
            st.markdown("**Actions**")
            
            if st.button(":material/delete: Clear Documents", use_container_width=True):
                st.session_state.uploaded_documents = []
                st.session_state.ingested_sources = []
                st.success("Documents cleared")
            
            if st.button(":material/delete: Clear Chat History", use_container_width=True):
                st.session_state.messages = []
                st.success("Chat history cleared")
            
            if st.button(":material/delete: Clear Portfolio", use_container_width=True):
                st.session_state.portfolio = {}
                st.success("Portfolio cleared")
            
            if st.button(":material/delete: Clear Watchlist", use_container_width=True):
                st.session_state.watchlist = []
                st.success("Watchlist cleared")
        
        st.divider()
        
        # Export/Import settings
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(":material/download: Export All Data", use_container_width=True):
                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "portfolio": st.session_state.portfolio,
                    "watchlist": st.session_state.watchlist,
                    "tracked_tickers": st.session_state.tracked_tickers,
                    "settings": {
                        "cortex_model": st.session_state.cortex_model,
                        "temperature": st.session_state.temperature,
                        "max_tokens": st.session_state.max_tokens,
                    }
                }
                
                st.download_button(
                    label=":material/download: Download JSON",
                    data=json.dumps(export_data, indent=2, default=str),
                    file_name=f"jse_dss_export_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True,
                )
        
        with col2:
            uploaded_config = st.file_uploader(
                "Import configuration",
                type=["json"],
                key="config_import"
            )
            
            if uploaded_config:
                try:
                    config_data = json.load(uploaded_config)
                    
                    if st.button(":material/upload: Apply Configuration", use_container_width=True):
                        if "portfolio" in config_data:
                            st.session_state.portfolio = config_data["portfolio"]
                        if "watchlist" in config_data:
                            st.session_state.watchlist = config_data["watchlist"]
                        if "tracked_tickers" in config_data:
                            st.session_state.tracked_tickers = config_data["tracked_tickers"]
                        if "settings" in config_data:
                            settings = config_data["settings"]
                            st.session_state.cortex_model = settings.get("cortex_model", "claude-3-5-sonnet")
                            st.session_state.temperature = settings.get("temperature", 0.3)
                            st.session_state.max_tokens = settings.get("max_tokens", 2048)
                        
                        st.success("Configuration imported!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to parse configuration: {e}")


def render_ui_settings():
    """Render UI preferences."""
    st.subheader(":material/palette: Display Preferences")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.toggle(
                "Compact view",
                key="compact_view",
                value=False,
                help="Use compact layout for data tables"
            )
            
            st.toggle(
                "Show tooltips",
                key="show_tooltips",
                value=True,
                help="Show helpful tooltips throughout the app"
            )
        
        with col2:
            st.selectbox(
                "Default currency",
                options=["ZAR", "USD", "EUR", "GBP"],
                key="default_currency",
                help="Currency for displaying monetary values"
            )
            
            st.selectbox(
                "Date format",
                options=["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"],
                key="date_format",
                help="Format for displaying dates"
            )


def render_about_section():
    """Render about section."""
    st.subheader(":material/info: About")
    
    with st.container(border=True):
        st.markdown("""
        ### JSE Decision-Support System
        
        A comprehensive platform for analyzing JSE-listed equities, powered by 
        Snowflake Cortex AI.
        
        **Features:**
        - Portfolio tracking and analysis
        - Company research with fundamental data
        - AI-powered document analysis (RAG)
        - SENS announcement monitoring
        - Multi-source data ingestion
        
        **Technology Stack:**
        - Streamlit in Snowflake
        - Snowflake Cortex LLM
        - Snowpark for data processing
        
        **Version:** 1.0.0  
        **Last Updated:** January 2026
        """)
        
        st.divider()
        
        st.caption("""
        **Disclaimer:** This application is a decision-support tool, not investment advice. 
        It does not provide price predictions. Always conduct your own research and consult 
        with qualified financial advisors before making investment decisions.
        """)


def render_cache_management():
    """Render cache management section."""
    st.subheader(":material/cached: Cache Management")
    
    with st.container(border=True):
        st.caption("Clear cached data to refresh from source")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(":material/refresh: Clear Data Cache", use_container_width=True):
                st.cache_data.clear()
                st.success("Data cache cleared")
        
        with col2:
            if st.button(":material/refresh: Clear Resource Cache", use_container_width=True):
                st.cache_resource.clear()
                st.success("Resource cache cleared (connections will be re-established)")


# Main page rendering
st.title(":material/settings: Settings")
st.caption("Configure your JSE Decision-Support System")

# Settings sections
tab1, tab2, tab3 = st.tabs([
    ":material/psychology: AI & Model",
    ":material/storage: Data & Connection",
    ":material/palette: Preferences"
])

with tab1:
    render_model_settings()
    st.divider()
    render_cache_management()

with tab2:
    render_connection_settings()
    st.divider()
    render_data_settings()

with tab3:
    render_ui_settings()
    st.divider()
    render_about_section()

# Sidebar with quick info
with st.sidebar:
    st.header(":material/info: System Info")
    
    is_sis = is_sis_environment()
    st.caption(f"Environment: {'SiS' if is_sis else 'Local/External'}")
    st.caption(f"Model: {st.session_state.cortex_model}")
    st.caption(f"Session started: {datetime.now().strftime('%Y-%m-%d')}")
    
    st.divider()
    
    st.header(":material/help: Help")
    st.caption("Need assistance? Check the documentation or contact support.")
    
    if st.button(":material/help: View Documentation", use_container_width=True):
        st.info("Documentation coming soon!")
