"""
Dashboard Page - Company management and data overview.
JSE Decision-Support System - ETL/RAG Platform
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Import utilities
import sys
sys.path.append("..")
from utils.data_utils import (
    JSE_SECTORS,
    validate_company_data,
    get_companies_by_sector,
)
from utils.snowflake_utils import get_session, execute_query


def render_add_company_form():
    """Render form to add a new company."""
    st.subheader(":material/add_business: Add Company")
    
    with st.form("add_company_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            ticker = st.text_input(
                "Ticker Symbol *",
                placeholder="e.g., NPN",
                help="2-5 letter ticker symbol",
                max_chars=5,
            ).upper().strip()
            
            sector = st.selectbox(
                "Sector *",
                options=JSE_SECTORS,
                help="Select the company's sector classification",
            )
        
        with col2:
            name = st.text_input(
                "Company Name *",
                placeholder="e.g., Naspers Limited",
                help="Full company name",
            ).strip()
            
            description = st.text_area(
                "Description (optional)",
                placeholder="Brief description of the company...",
                height=68,
            )
        
        submitted = st.form_submit_button(
            ":material/add: Add Company",
            type="primary",
            use_container_width=True,
        )
        
        if submitted:
            is_valid, error_msg = validate_company_data(ticker, name, sector)
            
            if not is_valid:
                st.error(error_msg)
            elif any(c["ticker"] == ticker for c in st.session_state.companies):
                st.error(f"Company with ticker '{ticker}' already exists")
            else:
                new_company = {
                    "ticker": ticker,
                    "name": name,
                    "sector": sector,
                    "description": description,
                    "added_at": datetime.now().isoformat(),
                    "documents_count": 0,
                }
                st.session_state.companies.append(new_company)
                st.success(f"Added {name} ({ticker}) to your companies")
                st.rerun()


def render_companies_overview():
    """Render overview of all tracked companies."""
    st.subheader(":material/business: Your Companies")
    
    companies = st.session_state.companies
    
    if not companies:
        st.info(
            "No companies added yet. Add your first company above to start "
            "ingesting data and building your research knowledge base."
        )
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Companies", len(companies))
    
    with col2:
        sectors_used = len(set(c["sector"] for c in companies))
        st.metric("Sectors Covered", sectors_used)
    
    with col3:
        total_docs = sum(c.get("documents_count", 0) for c in companies)
        st.metric("Documents Ingested", total_docs)
    
    with col4:
        st.metric("Watchlist", len(st.session_state.watchlist))
    
    st.divider()
    
    # View toggle
    view_mode = st.radio(
        "View",
        ["List", "By Sector", "Cards"],
        horizontal=True,
        key="companies_view_mode",
    )
    
    if view_mode == "List":
        render_companies_list(companies)
    elif view_mode == "By Sector":
        render_companies_by_sector(companies)
    else:
        render_companies_cards(companies)


def render_companies_list(companies: list):
    """Render companies in a table view."""
    df = pd.DataFrame(companies)
    
    # Add action column tracking
    for idx, company in enumerate(companies):
        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 1, 1])
        
        with col1:
            st.markdown(f"**{company['ticker']}**")
        
        with col2:
            st.write(company['name'])
        
        with col3:
            st.caption(company['sector'])
        
        with col4:
            docs = company.get('documents_count', 0)
            st.caption(f":material/description: {docs}")
        
        with col5:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button(":material/science:", key=f"research_{company['ticker']}", help="Research"):
                    st.session_state.selected_ticker = company['ticker']
                    st.switch_page("pages/company_research.py")
            with col_b:
                if st.button(":material/delete:", key=f"delete_{company['ticker']}", help="Remove"):
                    st.session_state.companies = [
                        c for c in companies if c['ticker'] != company['ticker']
                    ]
                    st.rerun()
        
        st.divider()


def render_companies_by_sector(companies: list):
    """Render companies grouped by sector."""
    sectors = get_companies_by_sector(companies)
    
    # Sector distribution chart
    sector_counts = pd.DataFrame([
        {"sector": s, "count": len(c)} 
        for s, c in sectors.items()
    ])
    
    if not sector_counts.empty:
        fig = px.pie(
            sector_counts,
            values="count",
            names="sector",
            title="Companies by Sector",
            hole=0.4,
        )
        fig.update_layout(margin=dict(t=40, l=0, r=0, b=0), height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Sector expandable sections
    for sector in JSE_SECTORS:
        sector_companies = sectors.get(sector, [])
        if sector_companies:
            with st.expander(f":material/folder: {sector} ({len(sector_companies)})", expanded=False):
                for company in sector_companies:
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.markdown(f"**{company['ticker']}**")
                    with col2:
                        st.write(company['name'])
                    with col3:
                        if st.button(":material/arrow_forward:", key=f"goto_{company['ticker']}"):
                            st.session_state.selected_ticker = company['ticker']
                            st.switch_page("pages/company_research.py")


def render_companies_cards(companies: list):
    """Render companies as cards."""
    cols = st.columns(3)
    
    for idx, company in enumerate(companies):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"### {company['ticker']}")
                st.write(company['name'])
                st.caption(f":material/category: {company['sector']}")
                
                docs = company.get('documents_count', 0)
                if docs > 0:
                    st.caption(f":material/description: {docs} documents")
                
                if company.get('description'):
                    st.caption(company['description'][:100] + "..." if len(company.get('description', '')) > 100 else company.get('description', ''))
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(":material/science: Research", key=f"card_research_{company['ticker']}", use_container_width=True):
                        st.session_state.selected_ticker = company['ticker']
                        st.switch_page("pages/company_research.py")
                with col2:
                    if st.button(":material/upload: Ingest", key=f"card_ingest_{company['ticker']}", use_container_width=True):
                        st.session_state.selected_ticker = company['ticker']
                        st.switch_page("pages/data_ingestion.py")


def render_watchlist():
    """Render watchlist section."""
    st.subheader(":material/visibility: Watchlist")
    
    companies = st.session_state.companies
    watchlist = st.session_state.watchlist
    
    if not companies:
        st.info("Add companies first to create a watchlist.")
        return
    
    # Add to watchlist
    available = [c["ticker"] for c in companies if c["ticker"] not in watchlist]
    
    if available:
        col1, col2 = st.columns([3, 1])
        with col1:
            selected = st.selectbox(
                "Add to watchlist",
                options=available,
                format_func=lambda t: f"{t} - {next((c['name'] for c in companies if c['ticker'] == t), t)}",
                key="watchlist_select",
            )
        with col2:
            if st.button(":material/add:", use_container_width=True, key="add_watch"):
                if selected:
                    st.session_state.watchlist.append(selected)
                    st.rerun()
    
    # Display watchlist
    if watchlist:
        for ticker in watchlist:
            company = next((c for c in companies if c["ticker"] == ticker), None)
            if company:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.markdown(f"**{ticker}**")
                    with col2:
                        st.caption(f"{company['name']} • {company['sector']}")
                    with col3:
                        if st.button(":material/close:", key=f"unwatch_{ticker}"):
                            st.session_state.watchlist.remove(ticker)
                            st.rerun()
    else:
        st.caption("Your watchlist is empty. Add companies to track them here.")


def render_data_status():
    """Render data ingestion status overview."""
    st.subheader(":material/database: Data Status")
    
    companies = st.session_state.companies
    documents = st.session_state.uploaded_documents
    
    if not companies:
        st.info("Add companies to see data status.")
        return
    
    # Documents per company
    doc_counts = {}
    for doc in documents:
        ticker = doc.get("ticker", "Unknown")
        doc_counts[ticker] = doc_counts.get(ticker, 0) + 1
    
    # Update company document counts
    for company in companies:
        company["documents_count"] = doc_counts.get(company["ticker"], 0)
    
    # Summary
    total_docs = len(documents)
    companies_with_docs = sum(1 for c in companies if c.get("documents_count", 0) > 0)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Documents", total_docs)
    with col2:
        st.metric("Companies with Data", f"{companies_with_docs}/{len(companies)}")
    
    # Companies needing data
    no_data = [c for c in companies if c.get("documents_count", 0) == 0]
    if no_data:
        st.warning(f"{len(no_data)} companies have no documents ingested")
        with st.expander("Companies needing data"):
            for c in no_data:
                st.write(f"• {c['ticker']} - {c['name']}")


# Main dashboard rendering
st.title(":material/dashboard: Dashboard")
st.caption("Manage your companies and track data ingestion")

# Initialize companies if not exists
if "companies" not in st.session_state:
    st.session_state.companies = []

# Main tabs
tab1, tab2, tab3 = st.tabs([
    ":material/business: Companies",
    ":material/visibility: Watchlist", 
    ":material/database: Data Status",
])

with tab1:
    render_add_company_form()
    st.divider()
    render_companies_overview()

with tab2:
    render_watchlist()

with tab3:
    render_data_status()

# Sidebar quick actions
with st.sidebar:
    st.header(":material/bolt: Quick Actions")
    
    if st.button(":material/upload_file: Ingest Data", use_container_width=True):
        st.switch_page("pages/data_ingestion.py")
    
    if st.button(":material/psychology: AI Analyst", use_container_width=True):
        st.switch_page("pages/ai_analyst.py")
    
    st.divider()
    
    st.subheader(":material/info: Summary")
    st.caption(f"Companies: {len(st.session_state.companies)}")
    st.caption(f"Watchlist: {len(st.session_state.watchlist)}")
    st.caption(f"Documents: {len(st.session_state.uploaded_documents)}")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
