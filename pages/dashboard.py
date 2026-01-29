"""
Dashboard Page - Portfolio overview, watchlist, and market summary.
JSE Decision-Support System
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Import utilities
import sys
sys.path.append("..")
from utils.data_utils import (
    format_currency, 
    format_percentage, 
    create_sample_portfolio,
    SAMPLE_JSE_TICKERS,
    JSE_SECTORS
)
from utils.snowflake_utils import get_session, execute_query


def render_portfolio_summary(portfolio_df: pd.DataFrame):
    """Render portfolio summary metrics."""
    total_value = portfolio_df["market_value"].sum()
    total_cost = portfolio_df["cost_basis"].sum()
    total_pnl = portfolio_df["unrealized_pnl"].sum()
    total_return = (total_value / total_cost - 1) if total_cost > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Portfolio Value",
            value=format_currency(total_value),
            delta=format_currency(total_pnl),
        )
    
    with col2:
        st.metric(
            label="Total Return",
            value=format_percentage(total_return),
            delta=f"{total_return*100:+.2f}%",
        )
    
    with col3:
        st.metric(
            label="Holdings",
            value=len(portfolio_df),
        )
    
    with col4:
        # Best performer
        best = portfolio_df.loc[portfolio_df["return_pct"].idxmax()]
        st.metric(
            label=f"Best: {best['ticker']}",
            value=f"{best['return_pct']:+.1f}%",
        )


def render_portfolio_allocation(portfolio_df: pd.DataFrame):
    """Render portfolio allocation charts."""
    col1, col2 = st.columns(2)
    
    with col1:
        # Allocation by holding
        fig = px.pie(
            portfolio_df,
            values="market_value",
            names="ticker",
            title="Allocation by Holding",
            hole=0.4,
        )
        fig.update_layout(margin=dict(t=40, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Allocation by sector
        sector_allocation = portfolio_df.groupby("sector")["market_value"].sum().reset_index()
        fig = px.pie(
            sector_allocation,
            values="market_value",
            names="sector",
            title="Allocation by Sector",
            hole=0.4,
        )
        fig.update_layout(margin=dict(t=40, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)


def render_holdings_table(portfolio_df: pd.DataFrame):
    """Render detailed holdings table."""
    st.subheader(":material/table_chart: Holdings")
    
    # Format for display
    display_df = portfolio_df.copy()
    display_df["return_pct"] = display_df["return_pct"].apply(lambda x: f"{x:+.2f}%")
    display_df["avg_price"] = display_df["avg_price"].apply(lambda x: f"R{x:,.2f}")
    display_df["current_price"] = display_df["current_price"].apply(lambda x: f"R{x:,.2f}")
    display_df["market_value"] = display_df["market_value"].apply(lambda x: f"R{x:,.2f}")
    display_df["unrealized_pnl"] = display_df["unrealized_pnl"].apply(lambda x: f"R{x:+,.2f}")
    
    st.dataframe(
        display_df[["ticker", "name", "sector", "shares", "avg_price", 
                    "current_price", "market_value", "unrealized_pnl", "return_pct"]],
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "name": st.column_config.TextColumn("Company", width="medium"),
            "sector": st.column_config.TextColumn("Sector", width="medium"),
            "shares": st.column_config.NumberColumn("Shares", format="%d"),
            "avg_price": st.column_config.TextColumn("Avg Price"),
            "current_price": st.column_config.TextColumn("Current"),
            "market_value": st.column_config.TextColumn("Value"),
            "unrealized_pnl": st.column_config.TextColumn("P&L"),
            "return_pct": st.column_config.TextColumn("Return"),
        },
        hide_index=True,
        use_container_width=True,
    )


def render_watchlist():
    """Render watchlist management."""
    st.subheader(":material/visibility: Watchlist")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Ticker selection
        available_tickers = [t["ticker"] for t in SAMPLE_JSE_TICKERS]
        selected = st.selectbox(
            "Add to watchlist",
            options=[t for t in available_tickers if t not in st.session_state.watchlist],
            key="watchlist_add_select"
        )
    
    with col2:
        if st.button(":material/add: Add", use_container_width=True, key="add_watchlist_btn"):
            if selected and selected not in st.session_state.watchlist:
                st.session_state.watchlist.append(selected)
                st.rerun()
    
    # Display watchlist
    if st.session_state.watchlist:
        watchlist_data = []
        for ticker in st.session_state.watchlist:
            ticker_info = next((t for t in SAMPLE_JSE_TICKERS if t["ticker"] == ticker), None)
            if ticker_info:
                # Simulated price data
                import random
                price = random.uniform(50, 500)
                change = random.uniform(-5, 5)
                watchlist_data.append({
                    "ticker": ticker,
                    "name": ticker_info["name"],
                    "price": f"R{price:.2f}",
                    "change": f"{change:+.2f}%",
                    "sector": ticker_info["sector"],
                })
        
        watchlist_df = pd.DataFrame(watchlist_data)
        
        for idx, row in watchlist_df.iterrows():
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                with col1:
                    st.markdown(f"**{row['ticker']}**")
                with col2:
                    st.caption(row['name'])
                with col3:
                    st.markdown(f"{row['price']}")
                with col4:
                    change_color = "green" if "+" in row['change'] else "red"
                    st.markdown(f":{change_color}[{row['change']}]")
                    if st.button(":material/delete:", key=f"remove_{row['ticker']}", help="Remove"):
                        st.session_state.watchlist.remove(row['ticker'])
                        st.rerun()
    else:
        st.info("Your watchlist is empty. Add tickers above to track them.")


def render_market_overview():
    """Render market overview section."""
    st.subheader(":material/trending_up: Market Overview")
    
    # Simulated market indices
    col1, col2, col3 = st.columns(3)
    
    import random
    
    with col1:
        with st.container(border=True):
            change = random.uniform(-2, 2)
            st.metric(
                "JSE All Share",
                f"{random.randint(75000, 85000):,}",
                f"{change:+.2f}%"
            )
    
    with col2:
        with st.container(border=True):
            change = random.uniform(-2, 2)
            st.metric(
                "JSE Top 40",
                f"{random.randint(68000, 78000):,}",
                f"{change:+.2f}%"
            )
    
    with col3:
        with st.container(border=True):
            change = random.uniform(-1, 1)
            st.metric(
                "USD/ZAR",
                f"R{random.uniform(17.5, 19.5):.4f}",
                f"{change:+.2f}%"
            )


def render_sector_performance():
    """Render sector performance heatmap."""
    st.subheader(":material/grid_view: Sector Performance")
    
    import random
    
    # Simulated sector performance
    sector_data = []
    for sector in JSE_SECTORS:
        sector_data.append({
            "sector": sector,
            "daily": random.uniform(-3, 3),
            "weekly": random.uniform(-5, 5),
            "monthly": random.uniform(-10, 10),
        })
    
    sector_df = pd.DataFrame(sector_data)
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=[sector_df["daily"].values, sector_df["weekly"].values, sector_df["monthly"].values],
        x=sector_df["sector"].values,
        y=["Daily", "Weekly", "Monthly"],
        colorscale="RdYlGn",
        zmid=0,
        text=[[f"{v:.1f}%" for v in sector_df["daily"].values],
              [f"{v:.1f}%" for v in sector_df["weekly"].values],
              [f"{v:.1f}%" for v in sector_df["monthly"].values]],
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate="Sector: %{x}<br>Period: %{y}<br>Return: %{text}<extra></extra>",
    ))
    
    fig.update_layout(
        margin=dict(t=20, l=0, r=0, b=0),
        height=200,
        xaxis_tickangle=-45,
    )
    
    st.plotly_chart(fig, use_container_width=True)


# Main dashboard rendering
st.title(":material/dashboard: Dashboard")
st.caption("Portfolio overview and market summary")

# Initialize portfolio if empty
if not st.session_state.portfolio:
    st.session_state.portfolio = create_sample_portfolio()

portfolio_df = pd.DataFrame(st.session_state.portfolio)

# Tabs for different views
tab1, tab2, tab3 = st.tabs([
    ":material/account_balance_wallet: Portfolio",
    ":material/visibility: Watchlist",
    ":material/public: Market"
])

with tab1:
    if not portfolio_df.empty:
        render_portfolio_summary(portfolio_df)
        st.divider()
        render_portfolio_allocation(portfolio_df)
        st.divider()
        render_holdings_table(portfolio_df)
    else:
        st.info("No portfolio data available. Go to Data Ingestion to load your holdings.")

with tab2:
    render_watchlist()

with tab3:
    render_market_overview()
    st.divider()
    render_sector_performance()

# Quick actions in sidebar
with st.sidebar:
    st.header(":material/bolt: Quick Actions")
    
    if st.button(":material/refresh: Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    if st.button(":material/psychology: Ask AI Analyst", use_container_width=True):
        st.switch_page("pages/ai_analyst.py")
    
    st.divider()
    
    st.subheader(":material/info: Data Status")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption(f"Holdings: {len(portfolio_df)}")
    st.caption(f"Watchlist: {len(st.session_state.watchlist)} tickers")
    st.caption(f"Documents: {len(st.session_state.uploaded_documents)}")
