"""
Company Research Page - Deep-dive analysis and document exploration.
JSE Decision-Support System - ETL/RAG Platform
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

import sys
sys.path.append("..")
from utils.data_utils import (
    format_currency,
    format_percentage,
    JSE_SECTORS,
)
from utils.cortex_utils import (
    call_cortex_complete,
    build_analysis_prompt,
    build_rag_prompt,
    stream_cortex_response,
)
from utils.snowflake_utils import get_session, execute_query


def get_company_documents(ticker: str) -> list:
    """Get all documents associated with a company."""
    return [
        doc for doc in st.session_state.uploaded_documents
        if doc.get("ticker") == ticker
    ]


def render_company_header(company: dict):
    """Render company header with basic info."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header(f"{company['name']} ({company['ticker']})")
        st.caption(f":material/category: {company['sector']}")
        
        if company.get("description"):
            st.write(company["description"])
    
    with col2:
        docs = get_company_documents(company["ticker"])
        st.metric("Documents", len(docs))
        
        if company["ticker"] in st.session_state.watchlist:
            if st.button(":material/visibility_off: Unwatch", use_container_width=True):
                st.session_state.watchlist.remove(company["ticker"])
                st.rerun()
        else:
            if st.button(":material/visibility: Watch", use_container_width=True):
                st.session_state.watchlist.append(company["ticker"])
                st.rerun()


def render_documents_section(company: dict):
    """Render documents section for a company."""
    st.subheader(":material/description: Documents")
    
    docs = get_company_documents(company["ticker"])
    
    if not docs:
        st.info(
            f"No documents ingested for {company['ticker']} yet. "
            "Upload annual reports, SENS announcements, research notes, or other company data."
        )
        
        if st.button(":material/upload_file: Go to Data Ingestion", type="primary"):
            st.session_state.selected_ticker = company["ticker"]
            st.switch_page("pages/data_ingestion.py")
        return
    
    # Document type breakdown
    doc_types = {}
    for doc in docs:
        dtype = doc.get("type", "Other")
        doc_types[dtype] = doc_types.get(dtype, 0) + 1
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.caption("**Document Types**")
        for dtype, count in doc_types.items():
            st.write(f"• {dtype}: {count}")
    
    with col2:
        if len(doc_types) > 1:
            fig = px.pie(
                pd.DataFrame([{"type": k, "count": v} for k, v in doc_types.items()]),
                values="count",
                names="type",
                hole=0.5,
            )
            fig.update_layout(
                margin=dict(t=0, l=0, r=0, b=0),
                height=150,
                showlegend=True,
                legend=dict(orientation="h"),
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Document list
    for doc in docs:
        with st.expander(f":material/description: {doc['name']}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.caption(f"Type: {doc.get('type', 'Unknown')}")
                st.caption(f"Uploaded: {doc.get('uploaded_at', 'Unknown')}")
                
                if doc.get("summary"):
                    st.write("**Summary:**")
                    st.write(doc["summary"])
            
            with col2:
                if st.button(":material/psychology: Analyze", key=f"analyze_{doc['name']}"):
                    st.session_state.chat_context = {
                        "type": "document",
                        "ticker": company["ticker"],
                        "company_name": company["name"],
                        "document": doc,
                    }
                    st.switch_page("pages/ai_analyst.py")
            
            # Show preview if available
            content = doc.get("content", "")
            if content:
                st.text_area(
                    "Preview",
                    value=content[:1000] + "..." if len(content) > 1000 else content,
                    height=150,
                    disabled=True,
                    key=f"preview_{doc['name']}",
                )


def render_ai_research(company: dict):
    """Render AI-powered research section."""
    st.subheader(":material/psychology: AI Research Assistant")
    
    docs = get_company_documents(company["ticker"])
    
    if not docs:
        st.warning(
            "No documents available for RAG. Upload company documents first "
            "to enable AI-powered research."
        )
        return
    
    # Research mode selection
    research_mode = st.radio(
        "Research Mode",
        ["Ask a Question", "Generate Summary", "Extract Key Data"],
        horizontal=True,
        key="research_mode",
    )
    
    if research_mode == "Ask a Question":
        question = st.text_input(
            "Your question",
            placeholder=f"What are the key risks mentioned in {company['name']}'s reports?",
            key="research_question",
        )
        
        if st.button(":material/send: Ask", type="primary", disabled=not question):
            # Build context from documents
            context_parts = []
            for doc in docs[:5]:  # Limit to 5 docs
                content = doc.get("content", "")[:3000]  # Limit content
                context_parts.append(f"[{doc['name']}]\n{content}")
            
            context = "\n\n---\n\n".join(context_parts)
            
            prompt = build_rag_prompt(
                retrieved_chunks=[{"source": d["name"], "text": d.get("content", "")[:2000]} for d in docs[:5]],
                question=question,
                ticker=company["ticker"],
            )
            
            with st.chat_message("assistant"):
                with st.spinner("Researching..."):
                    response = st.write_stream(stream_cortex_response(
                        prompt,
                        model=st.session_state.cortex_model,
                    ))
    
    elif research_mode == "Generate Summary":
        summary_type = st.selectbox(
            "Summary Type",
            ["Executive Overview", "Financial Highlights", "Risk Factors", "Strategic Outlook"],
            key="summary_type",
        )
        
        if st.button(":material/auto_awesome: Generate", type="primary"):
            # Build context
            all_content = "\n\n".join([d.get("content", "")[:2000] for d in docs[:5]])
            
            prompts = {
                "Executive Overview": f"Based on the following documents for {company['name']}, provide a concise executive overview covering the company's business, recent performance, and outlook.",
                "Financial Highlights": f"Extract and summarize the key financial metrics and highlights from these {company['name']} documents. Focus on revenue, profitability, growth rates, and financial health indicators.",
                "Risk Factors": f"Identify and summarize the main risk factors mentioned in these {company['name']} documents. Categorize them by type (operational, financial, market, regulatory, etc.).",
                "Strategic Outlook": f"Based on these documents, summarize {company['name']}'s strategic direction, initiatives, and management's outlook for the future.",
            }
            
            prompt = build_analysis_prompt(
                context=all_content,
                question=prompts[summary_type],
                analysis_type="fundamental",
            )
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing documents..."):
                    response = st.write_stream(stream_cortex_response(
                        prompt,
                        model=st.session_state.cortex_model,
                    ))
    
    else:  # Extract Key Data
        data_type = st.selectbox(
            "Data to Extract",
            ["Financial Metrics", "Key Personnel", "Important Dates", "Entities & Relationships"],
            key="extract_type",
        )
        
        if st.button(":material/table_chart: Extract", type="primary"):
            all_content = "\n\n".join([d.get("content", "")[:2000] for d in docs[:5]])
            
            extract_prompts = {
                "Financial Metrics": "Extract all financial metrics, ratios, and numbers from these documents. Format as a structured list with metric name, value, and period/context.",
                "Key Personnel": "Extract all names and roles of key personnel (executives, board members, auditors) mentioned in these documents.",
                "Important Dates": "Extract all significant dates mentioned (reporting dates, AGM dates, dividend dates, deadlines, etc.) from these documents.",
                "Entities & Relationships": "Extract all company names, subsidiaries, partners, and competitors mentioned, along with their relationship to the main company.",
            }
            
            prompt = f"""Analyze the following documents for {company['name']} and {extract_prompts[data_type]}

DOCUMENTS:
{all_content}

Provide structured, well-organized output."""
            
            with st.chat_message("assistant"):
                with st.spinner("Extracting data..."):
                    response = st.write_stream(stream_cortex_response(
                        prompt,
                        model=st.session_state.cortex_model,
                    ))


def render_notes_section(company: dict):
    """Render research notes section."""
    st.subheader(":material/edit_note: Research Notes")
    
    # Initialize notes storage
    if "company_notes" not in st.session_state:
        st.session_state.company_notes = {}
    
    ticker = company["ticker"]
    current_notes = st.session_state.company_notes.get(ticker, "")
    
    notes = st.text_area(
        "Your notes",
        value=current_notes,
        height=200,
        placeholder=f"Add your research notes for {company['name']}...",
        key=f"notes_{ticker}",
    )
    
    if st.button(":material/save: Save Notes"):
        st.session_state.company_notes[ticker] = notes
        st.success("Notes saved!")


def render_no_company_selected():
    """Render view when no company is selected."""
    st.info("Select a company to research or add companies from the Dashboard.")
    
    companies = st.session_state.get("companies", [])
    
    if companies:
        st.subheader("Your Companies")
        
        cols = st.columns(3)
        for idx, company in enumerate(companies):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"**{company['ticker']}**")
                    st.caption(company['name'])
                    st.caption(f":material/category: {company['sector']}")
                    
                    if st.button(":material/science: Research", key=f"select_{company['ticker']}", use_container_width=True):
                        st.session_state.selected_ticker = company['ticker']
                        st.rerun()
    else:
        if st.button(":material/add_business: Add Your First Company", type="primary"):
            st.switch_page("pages/dashboard.py")


# Main page rendering
st.title(":material/science: Company Research")
st.caption("Deep-dive analysis and document exploration")

# Initialize state
if "companies" not in st.session_state:
    st.session_state.companies = []

companies = st.session_state.companies

# Company selector
if companies:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ticker_options = {f"{c['ticker']} - {c['name']}": c['ticker'] for c in companies}
        
        # Pre-select if coming from another page
        default_idx = 0
        if st.session_state.get("selected_ticker"):
            for idx, (display, ticker) in enumerate(ticker_options.items()):
                if ticker == st.session_state.selected_ticker:
                    default_idx = idx
                    break
        
        selected_display = st.selectbox(
            "Select Company",
            options=list(ticker_options.keys()),
            index=default_idx,
            key="research_company_select",
        )
        selected_ticker = ticker_options[selected_display]
        st.session_state.selected_ticker = selected_ticker
    
    with col2:
        if st.button(":material/add_business: Add New", use_container_width=True):
            st.switch_page("pages/dashboard.py")
    
    # Get selected company
    company = next((c for c in companies if c["ticker"] == selected_ticker), None)
    
    if company:
        render_company_header(company)
        
        st.divider()
        
        # Research tabs
        tab1, tab2, tab3 = st.tabs([
            ":material/description: Documents",
            ":material/psychology: AI Research",
            ":material/edit_note: Notes",
        ])
        
        with tab1:
            render_documents_section(company)
        
        with tab2:
            render_ai_research(company)
        
        with tab3:
            render_notes_section(company)

else:
    render_no_company_selected()

# Sidebar
with st.sidebar:
    st.header(":material/quick_reference: Quick Actions")
    
    if st.button(":material/upload_file: Ingest Documents", use_container_width=True):
        st.switch_page("pages/data_ingestion.py")
    
    if st.button(":material/psychology: AI Analyst", use_container_width=True):
        st.switch_page("pages/ai_analyst.py")
    
    st.divider()
    
    # Watchlist quick view
    st.subheader(":material/visibility: Watchlist")
    watchlist = st.session_state.get("watchlist", [])
    
    if watchlist and companies:
        for ticker in watchlist[:5]:
            company = next((c for c in companies if c["ticker"] == ticker), None)
            if company:
                if st.button(f"{ticker}", key=f"watch_{ticker}", use_container_width=True):
                    st.session_state.selected_ticker = ticker
                    st.rerun()
    else:
        st.caption("No companies in watchlist")
