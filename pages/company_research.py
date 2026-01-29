"""
Company Research Page - Deep-dive analysis per equity.
JSE Decision-Support System
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

import sys
sys.path.append("..")
from utils.data_utils import (
    format_currency,
    format_percentage,
    format_number,
    SAMPLE_JSE_TICKERS,
)
from utils.cortex_utils import (
    call_cortex_complete,
    build_analysis_prompt,
    stream_cortex_response,
)
from utils.snowflake_utils import get_session, execute_query


def generate_sample_price_data(ticker: str, days: int = 365) -> pd.DataFrame:
    """Generate sample price data for demonstration."""
    import numpy as np
    
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Random walk with drift
    np.random.seed(hash(ticker) % 2**32)
    initial_price = random.uniform(50, 500)
    returns = np.random.normal(0.0005, 0.02, days)
    prices = initial_price * np.cumprod(1 + returns)
    
    # Add some volume
    volume = np.random.randint(100000, 5000000, days)
    
    return pd.DataFrame({
        'date': dates,
        'close': prices,
        'volume': volume,
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, days))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, days))),
        'open': np.roll(prices, 1),
    })


def generate_sample_fundamentals(ticker: str) -> dict:
    """Generate sample fundamental data for demonstration."""
    random.seed(hash(ticker))
    
    return {
        "market_cap": random.uniform(10e9, 500e9),
        "pe_ratio": random.uniform(8, 35),
        "pb_ratio": random.uniform(0.5, 5),
        "dividend_yield": random.uniform(0, 0.08),
        "roe": random.uniform(0.05, 0.35),
        "roa": random.uniform(0.02, 0.15),
        "debt_to_equity": random.uniform(0, 2),
        "current_ratio": random.uniform(0.8, 3),
        "revenue_growth": random.uniform(-0.1, 0.3),
        "earnings_growth": random.uniform(-0.2, 0.4),
        "gross_margin": random.uniform(0.15, 0.6),
        "operating_margin": random.uniform(0.05, 0.3),
        "net_margin": random.uniform(0.02, 0.2),
        "beta": random.uniform(0.5, 1.8),
        "52w_high": random.uniform(100, 600),
        "52w_low": random.uniform(50, 300),
    }


def render_price_chart(price_df: pd.DataFrame, ticker: str):
    """Render interactive price chart."""
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=price_df['date'],
        open=price_df['open'],
        high=price_df['high'],
        low=price_df['low'],
        close=price_df['close'],
        name='Price',
    ))
    
    # Add moving averages
    price_df['ma_20'] = price_df['close'].rolling(window=20).mean()
    price_df['ma_50'] = price_df['close'].rolling(window=50).mean()
    
    fig.add_trace(go.Scatter(
        x=price_df['date'],
        y=price_df['ma_20'],
        name='20-day MA',
        line=dict(color='orange', width=1),
    ))
    
    fig.add_trace(go.Scatter(
        x=price_df['date'],
        y=price_df['ma_50'],
        name='50-day MA',
        line=dict(color='blue', width=1),
    ))
    
    fig.update_layout(
        title=f"{ticker} Price Chart",
        yaxis_title="Price (ZAR)",
        xaxis_title="Date",
        xaxis_rangeslider_visible=False,
        height=400,
        margin=dict(t=40, l=0, r=0, b=0),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_volume_chart(price_df: pd.DataFrame):
    """Render volume chart."""
    fig = px.bar(
        price_df.tail(90),
        x='date',
        y='volume',
        title='Trading Volume (90 days)',
    )
    fig.update_layout(
        height=200,
        margin=dict(t=40, l=0, r=0, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_fundamental_metrics(fundamentals: dict, ticker: str):
    """Render fundamental metrics cards."""
    st.subheader(":material/analytics: Fundamental Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container(border=True):
            st.metric("Market Cap", format_currency(fundamentals["market_cap"]))
            st.metric("P/E Ratio", f"{fundamentals['pe_ratio']:.1f}x")
            st.metric("P/B Ratio", f"{fundamentals['pb_ratio']:.1f}x")
    
    with col2:
        with st.container(border=True):
            st.metric("Dividend Yield", format_percentage(fundamentals["dividend_yield"]))
            st.metric("ROE", format_percentage(fundamentals["roe"]))
            st.metric("ROA", format_percentage(fundamentals["roa"]))
    
    with col3:
        with st.container(border=True):
            st.metric("D/E Ratio", f"{fundamentals['debt_to_equity']:.2f}")
            st.metric("Current Ratio", f"{fundamentals['current_ratio']:.2f}")
            st.metric("Beta", f"{fundamentals['beta']:.2f}")
    
    with col4:
        with st.container(border=True):
            st.metric("Revenue Growth", format_percentage(fundamentals["revenue_growth"]))
            st.metric("Earnings Growth", format_percentage(fundamentals["earnings_growth"]))
            st.metric("Net Margin", format_percentage(fundamentals["net_margin"]))


def render_margin_analysis(fundamentals: dict):
    """Render margin analysis chart."""
    margins = pd.DataFrame({
        'Metric': ['Gross Margin', 'Operating Margin', 'Net Margin'],
        'Value': [
            fundamentals['gross_margin'] * 100,
            fundamentals['operating_margin'] * 100,
            fundamentals['net_margin'] * 100,
        ]
    })
    
    fig = px.bar(
        margins,
        x='Metric',
        y='Value',
        title='Margin Analysis (%)',
        color='Metric',
        color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c'],
    )
    fig.update_layout(
        height=300,
        margin=dict(t=40, l=0, r=0, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_ai_analysis(ticker: str, company_name: str, fundamentals: dict, price_df: pd.DataFrame):
    """Render AI-powered analysis section."""
    st.subheader(":material/psychology: AI Analysis")
    
    analysis_type = st.selectbox(
        "Analysis Type",
        ["Fundamental Overview", "Technical Analysis", "Risk Assessment", "Custom Question"],
        key="analysis_type_select"
    )
    
    if analysis_type == "Custom Question":
        custom_question = st.text_input(
            "Your question about this company:",
            placeholder=f"What are the key risks for {ticker}?",
            key="custom_question_input"
        )
    else:
        custom_question = None
    
    if st.button(":material/auto_awesome: Generate Analysis", type="primary", use_container_width=True):
        # Build context from available data
        context = f"""
Company: {company_name} ({ticker})
Sector: {next((t['sector'] for t in SAMPLE_JSE_TICKERS if t['ticker'] == ticker), 'Unknown')}

FUNDAMENTAL DATA:
- Market Cap: {format_currency(fundamentals['market_cap'])}
- P/E Ratio: {fundamentals['pe_ratio']:.1f}x
- P/B Ratio: {fundamentals['pb_ratio']:.1f}x
- Dividend Yield: {format_percentage(fundamentals['dividend_yield'])}
- ROE: {format_percentage(fundamentals['roe'])}
- ROA: {format_percentage(fundamentals['roa'])}
- Debt/Equity: {fundamentals['debt_to_equity']:.2f}
- Current Ratio: {fundamentals['current_ratio']:.2f}
- Revenue Growth: {format_percentage(fundamentals['revenue_growth'])}
- Earnings Growth: {format_percentage(fundamentals['earnings_growth'])}
- Gross Margin: {format_percentage(fundamentals['gross_margin'])}
- Operating Margin: {format_percentage(fundamentals['operating_margin'])}
- Net Margin: {format_percentage(fundamentals['net_margin'])}
- Beta: {fundamentals['beta']:.2f}

PRICE DATA:
- Current Price: R{price_df['close'].iloc[-1]:.2f}
- 52-Week High: R{fundamentals['52w_high']:.2f}
- 52-Week Low: R{fundamentals['52w_low']:.2f}
- 20-day MA: R{price_df['close'].rolling(20).mean().iloc[-1]:.2f}
- 50-day MA: R{price_df['close'].rolling(50).mean().iloc[-1]:.2f}
- YTD Return: {((price_df['close'].iloc[-1] / price_df['close'].iloc[0]) - 1) * 100:.1f}%
"""
        
        # Determine question based on analysis type
        if analysis_type == "Fundamental Overview":
            question = f"Provide a comprehensive fundamental analysis of {company_name}. Assess valuation, profitability, financial health, and growth prospects. What should investors focus on?"
            analysis_mode = "fundamental"
        elif analysis_type == "Technical Analysis":
            question = f"Analyze the technical setup for {ticker}. Discuss price trends, moving averages, support/resistance levels, and potential scenarios."
            analysis_mode = "technical"
        elif analysis_type == "Risk Assessment":
            question = f"Identify and analyze the key risks for {company_name}. Consider financial, operational, market, and sector-specific risks."
            analysis_mode = "general"
        else:
            question = custom_question or f"Provide an overview of {company_name}"
            analysis_mode = "general"
        
        prompt = build_analysis_prompt(context, question, analysis_mode)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = st.write_stream(stream_cortex_response(
                    prompt, 
                    model=st.session_state.cortex_model
                ))


def render_related_documents(ticker: str):
    """Render related documents section."""
    st.subheader(":material/description: Related Documents")
    
    # Check for uploaded documents related to this ticker
    related_docs = [
        doc for doc in st.session_state.uploaded_documents
        if ticker.lower() in doc.get("name", "").lower() or
           ticker.lower() in doc.get("content", "").lower()[:500]
    ]
    
    if related_docs:
        for doc in related_docs:
            with st.expander(f":material/description: {doc['name']}"):
                st.caption(f"Uploaded: {doc.get('uploaded_at', 'Unknown')}")
                st.caption(f"Type: {doc.get('type', 'Unknown')}")
                if st.button(f"Analyze", key=f"analyze_doc_{doc['name']}"):
                    st.session_state.chat_context = {
                        "type": "document",
                        "ticker": ticker,
                        "document": doc,
                    }
                    st.switch_page("pages/ai_analyst.py")
    else:
        st.info(f"No documents found for {ticker}. Upload annual reports, filings, or research in Data Ingestion.")
        if st.button(":material/upload: Go to Data Ingestion"):
            st.switch_page("pages/data_ingestion.py")


# Main page rendering
st.title(":material/analytics: Company Research")
st.caption("Deep-dive analysis for JSE-listed equities")

# Ticker selection
col1, col2 = st.columns([2, 1])

with col1:
    ticker_options = {f"{t['ticker']} - {t['name']}": t['ticker'] for t in SAMPLE_JSE_TICKERS}
    selected_display = st.selectbox(
        "Select Company",
        options=list(ticker_options.keys()),
        key="research_ticker_select"
    )
    selected_ticker = ticker_options[selected_display]

with col2:
    if st.button(":material/add: Add to Watchlist", use_container_width=True):
        if selected_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(selected_ticker)
            st.success(f"Added {selected_ticker} to watchlist")
        else:
            st.info(f"{selected_ticker} already in watchlist")

# Store selected ticker
st.session_state.selected_ticker = selected_ticker

# Get company info
company_info = next((t for t in SAMPLE_JSE_TICKERS if t['ticker'] == selected_ticker), None)

if company_info:
    st.header(f"{company_info['name']} ({selected_ticker})")
    st.caption(f"Sector: {company_info['sector']}")
    
    # Generate sample data
    price_df = generate_sample_price_data(selected_ticker)
    fundamentals = generate_sample_fundamentals(selected_ticker)
    
    # Quick stats
    current_price = price_df['close'].iloc[-1]
    prev_price = price_df['close'].iloc[-2]
    daily_change = (current_price / prev_price - 1) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Price", f"R{current_price:.2f}", f"{daily_change:+.2f}%")
    with col2:
        st.metric("52W High", f"R{fundamentals['52w_high']:.2f}")
    with col3:
        st.metric("52W Low", f"R{fundamentals['52w_low']:.2f}")
    with col4:
        st.metric("Market Cap", format_currency(fundamentals['market_cap']))
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs([
        ":material/show_chart: Price",
        ":material/assessment: Fundamentals",
        ":material/psychology: AI Analysis",
        ":material/description: Documents"
    ])
    
    with tab1:
        render_price_chart(price_df, selected_ticker)
        render_volume_chart(price_df)
    
    with tab2:
        render_fundamental_metrics(fundamentals, selected_ticker)
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            render_margin_analysis(fundamentals)
        with col2:
            # Growth metrics chart
            growth_data = pd.DataFrame({
                'Metric': ['Revenue Growth', 'Earnings Growth'],
                'Value': [
                    fundamentals['revenue_growth'] * 100,
                    fundamentals['earnings_growth'] * 100,
                ]
            })
            fig = px.bar(
                growth_data,
                x='Metric',
                y='Value',
                title='Growth Metrics (%)',
                color='Metric',
                color_discrete_sequence=['#17becf', '#9467bd'],
            )
            fig.update_layout(height=300, margin=dict(t=40, l=0, r=0, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        render_ai_analysis(selected_ticker, company_info['name'], fundamentals, price_df)
    
    with tab4:
        render_related_documents(selected_ticker)

# Sidebar with quick actions
with st.sidebar:
    st.header(":material/compare_arrows: Compare")
    compare_ticker = st.selectbox(
        "Compare with",
        options=[t['ticker'] for t in SAMPLE_JSE_TICKERS if t['ticker'] != selected_ticker],
        key="compare_ticker_select"
    )
    
    if st.button(":material/compare: Compare", use_container_width=True):
        st.info("Comparison feature coming soon!")
    
    st.divider()
    
    st.header(":material/history: Recent Research")
    st.caption("Your recently viewed companies will appear here.")
