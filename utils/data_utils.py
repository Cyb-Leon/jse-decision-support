"""
Data processing utilities for JSE Decision-Support System.
Handles data transformation, validation, and formatting.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


# JSE Sector Classifications (user can add custom sectors)
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
    "Other",
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


def get_companies_by_sector(companies: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group companies by their sector.
    
    Args:
        companies: List of company dictionaries with 'sector' key
    
    Returns:
        Dictionary mapping sector names to lists of companies
    """
    sectors = {}
    for company in companies:
        sector = company.get("sector", "Other")
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(company)
    return sectors


def validate_company_data(ticker: str, name: str, sector: str) -> tuple:
    """
    Validate company data before adding.
    
    Args:
        ticker: Company ticker symbol
        name: Company name
        sector: Company sector
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not ticker or not ticker.strip():
        return False, "Ticker symbol is required"
    
    if not validate_ticker(ticker):
        return False, "Invalid ticker format (should be 2-5 letters)"
    
    if not name or not name.strip():
        return False, "Company name is required"
    
    if len(name.strip()) < 2:
        return False, "Company name too short"
    
    if not sector:
        return False, "Sector is required"
    
    return True, ""
