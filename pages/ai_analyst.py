"""
AI Analyst Page - RAG-powered chat for querying documents and data.
JSE Decision-Support System
"""
import streamlit as st
import pandas as pd
from datetime import datetime

import sys
sys.path.append("..")
from utils.cortex_utils import (
    call_cortex_complete,
    stream_cortex_response,
    build_analysis_prompt,
    build_rag_prompt,
    CORTEX_MODELS,
)
from utils.data_utils import SAMPLE_JSE_TICKERS


def get_relevant_context(question: str, ticker: str = None) -> str:
    """
    Retrieve relevant context from ingested data sources.
    
    Args:
        question: User's question
        ticker: Optional ticker symbol to focus on
    
    Returns:
        Relevant context string
    """
    context_parts = []
    
    # Search uploaded documents
    for doc in st.session_state.uploaded_documents:
        # Check if document is relevant
        doc_name = doc.get("name", "").lower()
        doc_content = doc.get("content", "")[:1000].lower()
        
        is_relevant = False
        if ticker and ticker.lower() in doc_name:
            is_relevant = True
        if ticker and ticker.lower() in doc_content:
            is_relevant = True
        if any(word in doc_name for word in question.lower().split()):
            is_relevant = True
        
        if is_relevant:
            if "chunks" in doc and doc["chunks"]:
                # Add first few relevant chunks
                for chunk in doc["chunks"][:3]:
                    context_parts.append(f"[Source: {doc['name']}]\n{chunk[:800]}")
            elif "content" in doc:
                context_parts.append(f"[Source: {doc['name']}]\n{doc['content'][:1500]}")
            elif "summary" in doc:
                context_parts.append(f"[Source: {doc['name']} - Summary]\n{doc['summary']}")
    
    # Add portfolio context if relevant
    if st.session_state.portfolio and any(word in question.lower() for word in ["portfolio", "holdings", "position"]):
        portfolio_df = pd.DataFrame(st.session_state.portfolio)
        context_parts.append(f"[Source: User Portfolio]\n{portfolio_df.to_string()}")
    
    # Add watchlist context
    if st.session_state.watchlist and "watchlist" in question.lower():
        context_parts.append(f"[Source: Watchlist]\nTickers being watched: {', '.join(st.session_state.watchlist)}")
    
    return "\n\n---\n\n".join(context_parts) if context_parts else ""


def render_chat_interface():
    """Render the main chat interface."""
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Show sources if available
            if msg.get("sources"):
                with st.expander(":material/source: Sources"):
                    for source in msg["sources"]:
                        st.caption(f"• {source}")
    
    # Chat input
    if prompt := st.chat_input("Ask about JSE equities, your portfolio, or uploaded documents..."):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat(),
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get selected ticker context
        selected_ticker = st.session_state.get("analyst_ticker_filter")
        
        # Retrieve relevant context
        context = get_relevant_context(prompt, selected_ticker)
        
        # Build prompt
        if context:
            # RAG-enhanced prompt
            full_prompt = f"""You are a senior financial analyst specializing in JSE-listed equities.
You have access to the user's documents, portfolio, and market data.
Answer questions based on the provided context. Always cite your sources.
Do not make price predictions - focus on analysis and insights.

AVAILABLE CONTEXT:
{context}

USER QUESTION:
{prompt}

Provide a thorough but concise analysis. Cite sources using [Source: name] notation.
If the context doesn't contain relevant information, say so and provide general guidance."""
        else:
            # General knowledge prompt
            full_prompt = f"""You are a senior financial analyst specializing in JSE-listed equities.
The user hasn't uploaded specific documents for this query.
Provide helpful analysis based on general financial principles.
Do not make price predictions - focus on frameworks and considerations.

USER QUESTION:
{prompt}

Note: For more specific analysis, suggest the user upload relevant documents or specify a ticker."""
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = st.write_stream(stream_cortex_response(
                    full_prompt,
                    model=st.session_state.cortex_model
                ))
        
        # Extract sources from context
        sources = []
        if context:
            import re
            source_matches = re.findall(r'\[Source: ([^\]]+)\]', context)
            sources = list(set(source_matches))
        
        # Save assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "sources": sources,
            "model": st.session_state.cortex_model,
        })


def render_quick_prompts():
    """Render quick prompt suggestions."""
    st.subheader(":material/lightbulb: Suggested Questions")
    
    selected_ticker = st.session_state.get("analyst_ticker_filter")
    
    if selected_ticker:
        prompts = [
            f"What are the key risks for {selected_ticker}?",
            f"Summarize the latest news about {selected_ticker}",
            f"How does {selected_ticker} compare to its sector peers?",
            f"What are the main growth drivers for {selected_ticker}?",
        ]
    else:
        prompts = [
            "Summarize my portfolio's sector exposure",
            "What are the key themes in my uploaded documents?",
            "Which of my holdings has the highest risk?",
            "Explain the current state of the JSE market",
        ]
    
    cols = st.columns(2)
    for i, prompt in enumerate(prompts):
        with cols[i % 2]:
            if st.button(prompt, key=f"quick_prompt_{i}", use_container_width=True):
                # Add prompt to messages and trigger response
                st.session_state.messages.append({
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.now().isoformat(),
                })
                st.rerun()


def render_context_panel():
    """Render the context configuration panel."""
    st.subheader(":material/tune: Analysis Context")
    
    # Ticker filter
    ticker_options = ["All"] + [t["ticker"] for t in SAMPLE_JSE_TICKERS]
    selected = st.selectbox(
        "Focus on ticker",
        options=ticker_options,
        key="analyst_ticker_filter_select"
    )
    st.session_state.analyst_ticker_filter = None if selected == "All" else selected
    
    # Analysis mode
    analysis_mode = st.selectbox(
        "Analysis mode",
        options=["General", "Fundamental", "Technical", "Sentiment", "News"],
        key="analysis_mode_select"
    )
    st.session_state.analysis_mode = analysis_mode.lower()
    
    # Model selection
    st.selectbox(
        "AI Model",
        options=CORTEX_MODELS,
        index=CORTEX_MODELS.index(st.session_state.cortex_model),
        key="analyst_model_select",
        on_change=lambda: setattr(st.session_state, 'cortex_model', st.session_state.analyst_model_select)
    )
    
    st.divider()
    
    # Available sources
    st.subheader(":material/folder: Available Sources")
    
    doc_count = len(st.session_state.uploaded_documents)
    st.caption(f":material/description: {doc_count} documents")
    
    if st.session_state.portfolio:
        st.caption(f":material/account_balance_wallet: Portfolio ({len(st.session_state.portfolio)} holdings)")
    
    if st.session_state.watchlist:
        st.caption(f":material/visibility: Watchlist ({len(st.session_state.watchlist)} tickers)")
    
    api_count = len(st.session_state.api_connections)
    if api_count:
        st.caption(f":material/api: {api_count} API connections")


def render_chat_history_panel():
    """Render chat history management."""
    st.subheader(":material/history: Chat History")
    
    if st.session_state.messages:
        st.caption(f"{len(st.session_state.messages)} messages")
        
        if st.button(":material/delete: Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # Export chat
        if st.button(":material/download: Export Chat", use_container_width=True):
            chat_export = []
            for msg in st.session_state.messages:
                chat_export.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp", ""),
                })
            
            import json
            chat_json = json.dumps(chat_export, indent=2)
            st.download_button(
                label=":material/download: Download JSON",
                data=chat_json,
                file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
            )
    else:
        st.caption("No messages yet")


# Main page rendering
st.title(":material/psychology: AI Analyst")
st.caption("RAG-powered analysis of your JSE equity data")

# Check for incoming context (e.g., from Company Research page)
if st.session_state.chat_context:
    context = st.session_state.chat_context
    if context.get("type") == "document":
        st.info(f"Analyzing document: {context.get('document', {}).get('name', 'Unknown')}")
    st.session_state.chat_context = None  # Clear after use

# Layout with main chat and sidebar
col_main, col_side = st.columns([3, 1])

with col_main:
    # Quick prompts if no messages
    if not st.session_state.messages:
        render_quick_prompts()
        st.divider()
    
    # Main chat interface
    render_chat_interface()

with col_side:
    render_context_panel()
    st.divider()
    render_chat_history_panel()

# Floating input hint
if not st.session_state.messages:
    st.info("""
    :material/info: **Getting Started**
    
    1. Upload documents in **Data Ingestion** for RAG-powered analysis
    2. Select a ticker to focus your analysis
    3. Ask questions about your portfolio, documents, or JSE equities
    
    The AI Analyst will cite sources from your uploaded documents.
    """)
