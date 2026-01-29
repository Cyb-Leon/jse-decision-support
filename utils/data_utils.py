"""
Data processing utilities for JSE Decision-Support System.
Handles data transformation, validation, and formatting.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


# JSE Sector Classifications
JSE_SECTORS = [
    "Basic Materials",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Real Estate",
    "Technology",
    "Telecommunications",
    "Utilities",
]

# Common JSE tickers for demo/testing
SAMPLE_JSE_TICKERS = [
    {"ticker": "NPN", "name": "Naspers Limited", "sector": "Consumer Discretionary"},
    {"ticker": "SOL", "name": "Sasol Limited", "sector": "Energy"},
    {"ticker": "SBK", "name": "Standard Bank Group", "sector": "Financials"},
    {"ticker": "AGL", "name": "Anglo American plc", "sector": "Basic Materials"},
    {"ticker": "BHP", "name": "BHP Group Limited", "sector": "Basic Materials"},
    {"ticker": "FSR", "name": "FirstRand Limited", "sector": "Financials"},
    {"ticker": "MTN", "name": "MTN Group Limited", "sector": "Telecommunications"},
    {"ticker": "VOD", "name": "Vodacom Group Limited", "sector": "Telecommunications"},
    {"ticker": "SHP", "name": "Shoprite Holdings", "sector": "Consumer Staples"},
    {"ticker": "CFR", "name": "Compagnie Financière Richemont", "sector": "Consumer Discretionary"},
    {"ticker": "ABG", "name": "Absa Group Limited", "sector": "Financials"},
    {"ticker": "NED", "name": "Nedbank Group Limited", "sector": "Financials"},
    {"ticker": "SLM", "name": "Sanlam Limited", "sector": "Financials"},
    {"ticker": "DSY", "name": "Discovery Limited", "sector": "Financials"},
    {"ticker": "BTI", "name": "British American Tobacco", "sector": "Consumer Staples"},
]


def format_currency(value: float, currency: str = "ZAR") -> str:
    """
    Format a value as currency.
    
    Args:
        value: Numeric value
        currency: Currency code (ZAR, USD, etc.)
    
    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"
    
    symbols = {"ZAR": "R", "USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency)
    
    if abs(value) >= 1e9:
        return f"{symbol}{value/1e9:.2f}B"
    elif abs(value) >= 1e6:
        return f"{symbol}{value/1e6:.2f}M"
    elif abs(value) >= 1e3:
        return f"{symbol}{value/1e3:.2f}K"
    else:
        return f"{symbol}{value:.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a value as percentage.
    
    Args:
        value: Numeric value (0.05 = 5%)
        decimals: Decimal places
    
    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """
    Format a large number with abbreviations.
    
    Args:
        value: Numeric value
        decimals: Decimal places
    
    Returns:
        Formatted number string
    """
    if value is None:
        return "N/A"
    
    if abs(value) >= 1e12:
        return f"{value/1e12:.{decimals}f}T"
    elif abs(value) >= 1e9:
        return f"{value/1e9:.{decimals}f}B"
    elif abs(value) >= 1e6:
        return f"{value/1e6:.{decimals}f}M"
    elif abs(value) >= 1e3:
        return f"{value/1e3:.{decimals}f}K"
    else:
        return f"{value:.{decimals}f}"


def calculate_returns(prices: pd.Series) -> Dict[str, float]:
    """
    Calculate various return metrics from a price series.
    
    Args:
        prices: Pandas Series of prices with datetime index
    
    Returns:
        Dictionary of return metrics
    """
    if prices.empty or len(prices) < 2:
        return {}
    
    returns = prices.pct_change().dropna()
    
    # Calculate metrics
    daily_return = returns.iloc[-1] if len(returns) > 0 else 0
    
    # Period returns
    metrics = {
        "daily_return": daily_return,
        "total_return": (prices.iloc[-1] / prices.iloc[0]) - 1,
    }
    
    # Weekly return (5 trading days)
    if len(prices) >= 5:
        metrics["weekly_return"] = (prices.iloc[-1] / prices.iloc[-5]) - 1
    
    # Monthly return (~21 trading days)
    if len(prices) >= 21:
        metrics["monthly_return"] = (prices.iloc[-1] / prices.iloc[-21]) - 1
    
    # YTD return
    current_year = datetime.now().year
    ytd_prices = prices[prices.index.year == current_year]
    if len(ytd_prices) >= 2:
        metrics["ytd_return"] = (ytd_prices.iloc[-1] / ytd_prices.iloc[0]) - 1
    
    # Volatility (annualized)
    if len(returns) >= 20:
        metrics["volatility"] = returns.std() * (252 ** 0.5)
    
    return metrics


def validate_ticker(ticker: str) -> bool:
    """
    Validate a JSE ticker format.
    
    Args:
        ticker: Ticker symbol to validate
    
    Returns:
        True if valid format, False otherwise
    """
    if not ticker:
        return False
    
    # JSE tickers are typically 2-5 uppercase letters
    ticker = ticker.strip().upper()
    return ticker.isalpha() and 2 <= len(ticker) <= 5


def parse_csv_upload(uploaded_file) -> Optional[pd.DataFrame]:
    """
    Parse an uploaded CSV file with error handling.
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Pandas DataFrame or None if parsing fails
    """
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Failed to parse CSV: {e}")
        return None


def parse_excel_upload(uploaded_file) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Parse an uploaded Excel file with multiple sheets.
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Dictionary of sheet name -> DataFrame or None if parsing fails
    """
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        sheets = {}
        for sheet_name in excel_file.sheet_names:
            sheets[sheet_name] = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        return sheets
    except Exception as e:
        st.error(f"Failed to parse Excel: {e}")
        return None


def extract_text_from_pdf(uploaded_file) -> Optional[str]:
    """
    Extract text from an uploaded PDF file.
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        import PyPDF2
        
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text_parts = []
        
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text())
        
        return "\n\n".join(text_parts)
    except ImportError:
        st.warning("PyPDF2 not installed. PDF text extraction unavailable.")
        return None
    except Exception as e:
        st.error(f"Failed to extract PDF text: {e}")
        return None


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for RAG.
    
    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end within last 20% of chunk
            search_start = end - int(chunk_size * 0.2)
            sentence_end = text.rfind('. ', search_start, end)
            if sentence_end != -1:
                end = sentence_end + 1
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    return chunks


def create_sample_portfolio() -> List[Dict[str, Any]]:
    """
    Create a sample portfolio for demonstration.
    
    Returns:
        List of portfolio holdings
    """
    import random
    
    sample_holdings = []
    selected_tickers = random.sample(SAMPLE_JSE_TICKERS, 5)
    
    for ticker_info in selected_tickers:
        # Generate random but realistic data
        shares = random.randint(100, 1000) * 10
        avg_price = random.uniform(50, 500)
        current_price = avg_price * random.uniform(0.8, 1.3)
        
        sample_holdings.append({
            "ticker": ticker_info["ticker"],
            "name": ticker_info["name"],
            "sector": ticker_info["sector"],
            "shares": shares,
            "avg_price": round(avg_price, 2),
            "current_price": round(current_price, 2),
            "market_value": round(shares * current_price, 2),
            "cost_basis": round(shares * avg_price, 2),
            "unrealized_pnl": round(shares * (current_price - avg_price), 2),
            "return_pct": round((current_price / avg_price - 1) * 100, 2),
        })
    
    return sample_holdings


def create_sample_sens_announcements() -> List[Dict[str, Any]]:
    """
    Create sample SENS announcements for demonstration.
    
    Returns:
        List of SENS announcement records
    """
    from datetime import datetime, timedelta
    
    announcements = [
        {
            "date": datetime.now() - timedelta(hours=2),
            "ticker": "NPN",
            "company": "Naspers Limited",
            "category": "Trading Statement",
            "headline": "Trading Statement for the six months ended 30 September 2025",
            "summary": "Headline earnings per share expected to increase by 15-20%",
            "sentiment": "positive",
        },
        {
            "date": datetime.now() - timedelta(hours=5),
            "ticker": "SBK",
            "company": "Standard Bank Group",
            "category": "Dividend Declaration",
            "headline": "Declaration of Final Dividend",
            "summary": "Final dividend of 620 cents per share declared",
            "sentiment": "positive",
        },
        {
            "date": datetime.now() - timedelta(days=1),
            "ticker": "SOL",
            "company": "Sasol Limited",
            "category": "Operational Update",
            "headline": "Production Update - Secunda Operations",
            "summary": "Planned maintenance shutdown completed ahead of schedule",
            "sentiment": "neutral",
        },
        {
            "date": datetime.now() - timedelta(days=1, hours=8),
            "ticker": "MTN",
            "company": "MTN Group Limited",
            "category": "Acquisition",
            "headline": "Acquisition of Fintech Startup",
            "summary": "MTN acquires mobile payments company for $150 million",
            "sentiment": "positive",
        },
        {
            "date": datetime.now() - timedelta(days=2),
            "ticker": "AGL",
            "company": "Anglo American plc",
            "category": "Production Report",
            "headline": "Q3 2025 Production Report",
            "summary": "Copper production up 8%, platinum group metals down 3%",
            "sentiment": "neutral",
        },
    ]
    
    return announcements
