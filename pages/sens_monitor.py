"""
SENS Monitor Page - Track JSE announcements and corporate actions.
JSE Decision-Support System - ETL/RAG Platform
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

import sys
sys.path.append("..")
from utils.cortex_utils import call_cortex_complete, stream_cortex_response


def render_announcement_card(announcement: dict):
    """Render a single SENS announcement card."""
    sentiment_colors = {
        "positive": "green",
        "negative": "red",
        "neutral": "gray",
    }
    
    sentiment = announcement.get("sentiment", "neutral")
    color = sentiment_colors.get(sentiment, "gray")
    
    with st.container(border=True):
        # Header row
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            st.markdown(f"**{announcement['ticker']}**")
        
        with col2:
            st.caption(announcement.get("company", announcement["ticker"]))
        
        with col3:
            # Format timestamp
            if isinstance(announcement.get("date"), datetime):
                time_ago = datetime.now() - announcement["date"]
                if time_ago.days > 0:
                    time_str = f"{time_ago.days}d ago"
                elif time_ago.seconds > 3600:
                    time_str = f"{time_ago.seconds // 3600}h ago"
                else:
                    time_str = f"{time_ago.seconds // 60}m ago"
            else:
                time_str = announcement.get("date", "Unknown")
            st.caption(time_str)
        
        # Category badge
        st.markdown(f":{color}[{announcement.get('category', 'Announcement')}]")
        
        # Headline
        st.markdown(f"**{announcement.get('headline', 'No headline')}**")
        
        # Summary
        if announcement.get("summary"):
            st.caption(announcement["summary"])
        
        # Actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(
                ":material/psychology: Analyze",
                key=f"analyze_{announcement['ticker']}_{hash(str(announcement))}",
                use_container_width=True
            ):
                st.session_state.sens_analysis_target = announcement
        
        with col2:
            if st.button(
                ":material/visibility: Research",
                key=f"research_{announcement['ticker']}_{hash(str(announcement))}",
                use_container_width=True
            ):
                st.session_state.selected_ticker = announcement["ticker"]
                st.switch_page("pages/company_research.py")
        
        with col3:
            if announcement["ticker"] not in st.session_state.tracked_tickers:
                if st.button(
                    ":material/notifications: Track",
                    key=f"track_{announcement['ticker']}_{hash(str(announcement))}",
                    use_container_width=True
                ):
                    st.session_state.tracked_tickers.append(announcement["ticker"])
                    st.success(f"Now tracking {announcement['ticker']}")


def render_announcement_analysis(announcement: dict):
    """Render AI analysis of a SENS announcement."""
    st.subheader(":material/psychology: AI Analysis")
    
    with st.container(border=True):
        st.markdown(f"**Analyzing:** {announcement.get('headline', 'Announcement')}")
        st.caption(f"Company: {announcement.get('company', announcement['ticker'])} ({announcement['ticker']})")
        
        prompt = f"""Analyze this JSE SENS announcement and provide insights for investors:

COMPANY: {announcement.get('company', announcement['ticker'])} ({announcement['ticker']})
CATEGORY: {announcement.get('category', 'General')}
HEADLINE: {announcement.get('headline', 'N/A')}
SUMMARY: {announcement.get('summary', 'N/A')}

Provide:
1. Key takeaways from this announcement
2. Potential impact on the company and shareholders
3. What investors should monitor going forward
4. Any red flags or positive signals

Do not make price predictions. Focus on analytical insights."""
        
        with st.spinner("Analyzing announcement..."):
            response = st.write_stream(stream_cortex_response(
                prompt,
                model=st.session_state.cortex_model
            ))
        
        if st.button(":material/close: Close Analysis"):
            st.session_state.sens_analysis_target = None
            st.rerun()


def render_add_announcement_form():
    """Render form to manually add a SENS announcement."""
    st.subheader(":material/add_circle: Add SENS Announcement")
    
    companies = st.session_state.get("companies", [])
    
    if not companies:
        st.info("Add companies first to track their SENS announcements.")
        if st.button(":material/add_business: Add Companies"):
            st.switch_page("pages/dashboard.py")
        return
    
    with st.form("add_sens_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            ticker_options = {f"{c['ticker']} - {c['name']}": c for c in companies}
            selected_display = st.selectbox(
                "Company *",
                options=list(ticker_options.keys()),
            )
            selected_company = ticker_options[selected_display]
            
            category = st.selectbox(
                "Category *",
                options=[
                    "Trading Statement",
                    "Dividend Declaration",
                    "Operational Update",
                    "Acquisition",
                    "Production Report",
                    "Director Dealings",
                    "Corporate Action",
                    "Results Announcement",
                    "Cautionary Announcement",
                    "Other",
                ],
            )
        
        with col2:
            headline = st.text_input(
                "Headline *",
                placeholder="e.g., Trading Statement for H1 2026",
            )
            
            sentiment = st.selectbox(
                "Sentiment",
                options=["neutral", "positive", "negative"],
            )
        
        summary = st.text_area(
            "Summary",
            placeholder="Brief summary of the announcement...",
            height=100,
        )
        
        submitted = st.form_submit_button(
            ":material/add: Add Announcement",
            type="primary",
            use_container_width=True,
        )
        
        if submitted:
            if not headline.strip():
                st.error("Headline is required")
            else:
                new_announcement = {
                    "ticker": selected_company["ticker"],
                    "company": selected_company["name"],
                    "category": category,
                    "headline": headline.strip(),
                    "summary": summary.strip(),
                    "sentiment": sentiment,
                    "date": datetime.now(),
                    "added_at": datetime.now().isoformat(),
                }
                st.session_state.sens_alerts.append(new_announcement)
                st.success(f"Added SENS announcement for {selected_company['ticker']}")
                st.rerun()


def render_filter_controls():
    """Render filter and search controls."""
    companies = st.session_state.get("companies", [])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Ticker filter
        ticker_options = ["All"] + [c["ticker"] for c in companies]
        st.session_state.sens_ticker_filter = st.selectbox(
            "Filter by ticker",
            options=ticker_options,
            key="sens_ticker_filter_select"
        )
    
    with col2:
        # Category filter
        categories = ["All", "Trading Statement", "Dividend Declaration", 
                     "Operational Update", "Acquisition", "Production Report",
                     "Director Dealings", "Corporate Action", "Results Announcement",
                     "Cautionary Announcement", "Other"]
        st.session_state.sens_category_filter = st.selectbox(
            "Filter by category",
            options=categories,
            key="sens_category_filter_select"
        )
    
    with col3:
        # Time filter
        time_options = ["All Time", "Today", "This Week", "This Month"]
        st.session_state.sens_time_filter = st.selectbox(
            "Time period",
            options=time_options,
            key="sens_time_filter_select"
        )


def filter_announcements(announcements: list) -> list:
    """Apply filters to announcements list."""
    filtered = announcements.copy()
    
    # Ticker filter
    ticker_filter = st.session_state.get("sens_ticker_filter", "All")
    if ticker_filter != "All":
        filtered = [a for a in filtered if a["ticker"] == ticker_filter]
    
    # Category filter
    category_filter = st.session_state.get("sens_category_filter", "All")
    if category_filter != "All":
        filtered = [a for a in filtered if a.get("category") == category_filter]
    
    # Time filter
    time_filter = st.session_state.get("sens_time_filter", "All Time")
    now = datetime.now()
    if time_filter != "All Time":
        filtered_by_time = []
        for a in filtered:
            if isinstance(a.get("date"), datetime):
                days_diff = (now - a["date"]).days
                if time_filter == "Today" and days_diff == 0:
                    filtered_by_time.append(a)
                elif time_filter == "This Week" and days_diff <= 7:
                    filtered_by_time.append(a)
                elif time_filter == "This Month" and days_diff <= 30:
                    filtered_by_time.append(a)
        filtered = filtered_by_time
    
    return filtered


def render_tracked_tickers():
    """Render tracked tickers management."""
    st.subheader(":material/notifications_active: Tracked Tickers")
    
    companies = st.session_state.get("companies", [])
    
    if st.session_state.tracked_tickers:
        for ticker in st.session_state.tracked_tickers:
            col1, col2 = st.columns([3, 1])
            with col1:
                company = next((c for c in companies if c["ticker"] == ticker), None)
                if company:
                    st.caption(f"**{ticker}** - {company['name']}")
                else:
                    st.caption(f"**{ticker}**")
            with col2:
                if st.button(":material/close:", key=f"untrack_{ticker}"):
                    st.session_state.tracked_tickers.remove(ticker)
                    st.rerun()
    else:
        st.caption("No tickers being tracked. Click 'Track' on announcements to add.")
    
    st.divider()
    
    # Add ticker manually
    if companies:
        available = [c["ticker"] for c in companies if c["ticker"] not in st.session_state.tracked_tickers]
        if available:
            col1, col2 = st.columns([2, 1])
            with col1:
                new_ticker = st.selectbox(
                    "Add ticker",
                    options=available,
                    key="add_tracked_ticker_select"
                )
            with col2:
                if st.button(":material/add:", use_container_width=True):
                    if new_ticker and new_ticker not in st.session_state.tracked_tickers:
                        st.session_state.tracked_tickers.append(new_ticker)
                        st.rerun()


def render_announcement_stats(announcements: list):
    """Render announcement statistics."""
    if not announcements:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Announcements", len(announcements))
    
    with col2:
        positive = len([a for a in announcements if a.get("sentiment") == "positive"])
        st.metric("Positive", positive)
    
    with col3:
        negative = len([a for a in announcements if a.get("sentiment") == "negative"])
        st.metric("Negative", negative)
    
    with col4:
        neutral = len([a for a in announcements if a.get("sentiment") == "neutral"])
        st.metric("Neutral", neutral)


def render_daily_digest():
    """Render AI-generated daily digest."""
    st.subheader(":material/summarize: Daily Digest")
    
    announcements = st.session_state.get("sens_alerts", [])
    
    if not announcements:
        st.info("No announcements to summarize. Add SENS announcements to generate a digest.")
        return
    
    if st.button(":material/auto_awesome: Generate Daily Summary", use_container_width=True):
        # Build summary prompt
        announcement_texts = []
        for a in announcements[:10]:  # Limit to 10 for prompt size
            announcement_texts.append(f"- {a['ticker']}: {a.get('headline', 'N/A')} ({a.get('category', 'N/A')})")
        
        prompt = f"""Summarize these JSE SENS announcements for an investor:

ANNOUNCEMENTS:
{chr(10).join(announcement_texts)}

Provide:
1. Key themes and trends
2. Notable corporate actions
3. Sectors showing activity
4. What investors should watch

Keep it concise and actionable."""
        
        with st.spinner("Generating digest..."):
            response = st.write_stream(stream_cortex_response(
                prompt,
                model=st.session_state.cortex_model
            ))


# Main page rendering
st.title(":material/notifications: SENS Monitor")
st.caption("Track JSE announcements and corporate actions")

# Initialize SENS-specific session state
st.session_state.setdefault("sens_analysis_target", None)
st.session_state.setdefault("sens_alerts", [])

# Get announcements from session state
announcements = st.session_state.get("sens_alerts", [])

# Check if we should show analysis
if st.session_state.sens_analysis_target:
    render_announcement_analysis(st.session_state.sens_analysis_target)
    st.divider()

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs([
    ":material/add_circle: Add",
    ":material/list: All Announcements",
    ":material/notifications_active: Tracked",
    ":material/summarize: Daily Digest"
])

with tab1:
    render_add_announcement_form()

with tab2:
    render_filter_controls()
    st.divider()
    
    filtered_announcements = filter_announcements(announcements)
    render_announcement_stats(filtered_announcements)
    
    st.divider()
    
    if filtered_announcements:
        for announcement in sorted(filtered_announcements, key=lambda x: x.get("date", datetime.min), reverse=True):
            render_announcement_card(announcement)
    else:
        st.info("No announcements yet. Add SENS announcements to track them.")

with tab3:
    # Show announcements only for tracked tickers
    if st.session_state.tracked_tickers:
        tracked_announcements = [
            a for a in announcements 
            if a["ticker"] in st.session_state.tracked_tickers
        ]
        if tracked_announcements:
            for announcement in sorted(tracked_announcements, key=lambda x: x.get("date", datetime.min), reverse=True):
                render_announcement_card(announcement)
        else:
            st.info("No recent announcements for your tracked tickers.")
    else:
        st.info("You're not tracking any tickers. Add tickers to get personalized alerts.")

with tab4:
    render_daily_digest()

# Sidebar with tracking management
with st.sidebar:
    render_tracked_tickers()
    
    st.divider()
    
    st.subheader(":material/settings: Alert Settings")
    
    st.toggle("Email alerts", key="email_alerts_toggle", value=False)
    st.toggle("Push notifications", key="push_alerts_toggle", value=False)
    
    st.selectbox(
        "Alert frequency",
        options=["Real-time", "Hourly digest", "Daily digest"],
        key="alert_frequency_select"
    )
    
    st.caption("Note: Alert delivery requires additional configuration.")
