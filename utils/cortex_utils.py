"""
Snowflake Cortex LLM utilities for JSE Decision-Support System.
Provides AI completion, search, and analysis capabilities.
"""
import streamlit as st
import json
import time
from utils.snowflake_utils import get_session


# Available Cortex models
CORTEX_MODELS = [
    "claude-3-5-sonnet",
    "claude-sonnet-4-5",
    "llama3.1-70b",
    "llama3.1-8b",
    "mistral-large",
    "mistral-7b",
]


@st.cache_data(show_spinner=False)
def call_cortex_complete(
    prompt: str,
    model: str = "claude-3-5-sonnet",
    temperature: float = 0.3,
    max_tokens: int = 2048
) -> str:
    """
    Call Snowflake Cortex LLM using ai_complete.
    
    Args:
        prompt: The prompt to send to the LLM
        model: Cortex model to use
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens in response
    
    Returns:
        LLM response text
    """
    session = get_session()
    if session is None:
        return "Error: No Snowflake session available"
    
    try:
        from snowflake.snowpark.functions import lit, col
        from snowflake.cortex import Complete
        
        # Use Cortex Complete function
        response = Complete(
            model=model,
            prompt=prompt,
            session=session
        )
        
        return response
        
    except ImportError:
        # Fallback to SQL-based approach
        try:
            escaped_prompt = prompt.replace("'", "''")
            result = session.sql(f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    '{model}',
                    '{escaped_prompt}'
                ) as response
            """).collect()
            
            response_raw = result[0]['RESPONSE']
            
            # Parse JSON response if needed
            try:
                response_json = json.loads(response_raw)
                if isinstance(response_json, dict) and "choices" in response_json:
                    return response_json["choices"][0]["messages"]
                return str(response_json)
            except json.JSONDecodeError:
                return response_raw
                
        except Exception as e:
            return f"Error calling Cortex: {str(e)}"


def stream_cortex_response(prompt: str, model: str = "claude-3-5-sonnet"):
    """
    Generator for streaming Cortex responses word-by-word.
    
    Args:
        prompt: The prompt to send to the LLM
        model: Cortex model to use
    
    Yields:
        Response text chunks
    """
    # Get full response first (Cortex doesn't natively stream via ai_complete)
    response_text = call_cortex_complete(prompt, model)
    
    # Stream word by word for better UX
    for word in response_text.split(" "):
        yield word + " "
        time.sleep(0.02)


def build_analysis_prompt(
    context: str,
    question: str,
    analysis_type: str = "general"
) -> str:
    """
    Build a structured prompt for financial analysis.
    
    Args:
        context: Relevant context (documents, data, etc.)
        question: User's question
        analysis_type: Type of analysis (general, fundamental, technical, sentiment)
    
    Returns:
        Formatted prompt string
    """
    system_prompts = {
        "general": """You are a senior financial analyst specializing in JSE-listed equities. 
Provide clear, well-reasoned analysis based on the provided context. 
Focus on actionable insights and always cite your sources from the context.
Do not make price predictions. Instead, highlight key factors that could influence investment decisions.""",
        
        "fundamental": """You are a fundamental analyst examining JSE-listed companies.
Focus on financial metrics, valuation ratios, earnings quality, and competitive positioning.
Analyze the provided data to assess the company's financial health and intrinsic value drivers.
Do not predict prices. Highlight strengths, weaknesses, and key metrics to monitor.""",
        
        "technical": """You are a technical analyst reviewing JSE equity charts and patterns.
Analyze price action, volume, support/resistance levels, and relevant indicators.
Identify key levels and patterns without making specific price predictions.
Focus on risk management and probability-based scenarios.""",
        
        "sentiment": """You are a market sentiment analyst covering JSE equities.
Analyze news, SENS announcements, and market commentary to gauge investor sentiment.
Identify key themes, concerns, and catalysts driving market perception.
Provide balanced view of bullish and bearish arguments.""",
        
        "news": """You are a financial news analyst covering JSE-listed companies.
Summarize key developments, corporate actions, and material announcements.
Assess potential impact on the company and its stakeholders.
Highlight what investors should monitor going forward."""
    }
    
    system_prompt = system_prompts.get(analysis_type, system_prompts["general"])
    
    prompt = f"""{system_prompt}

CONTEXT:
{context}

USER QUESTION:
{question}

Provide a thorough but concise analysis. Structure your response with clear sections where appropriate.
"""
    
    return prompt


def build_rag_prompt(
    retrieved_chunks: list,
    question: str,
    ticker: str = None
) -> str:
    """
    Build a RAG prompt with retrieved document chunks.
    
    Args:
        retrieved_chunks: List of relevant document chunks
        question: User's question
        ticker: Optional ticker symbol for context
    
    Returns:
        Formatted RAG prompt
    """
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        source = chunk.get("source", "Unknown")
        text = chunk.get("text", "")
        context_parts.append(f"[Source {i}: {source}]\n{text}")
    
    context = "\n\n".join(context_parts)
    
    ticker_context = f" for {ticker}" if ticker else ""
    
    prompt = f"""You are a financial research assistant analyzing JSE-listed equities{ticker_context}.

Based on the following retrieved documents, answer the user's question.
Always cite your sources using [Source N] notation.
If the documents don't contain relevant information, say so clearly.

RETRIEVED DOCUMENTS:
{context}

USER QUESTION:
{question}

Provide a well-structured answer with citations to the source documents.
"""
    
    return prompt


@st.cache_data(show_spinner=False, ttl=3600)
def summarize_document(document_text: str, max_length: int = 500) -> str:
    """
    Summarize a document using Cortex.
    
    Args:
        document_text: Full document text
        max_length: Target summary length
    
    Returns:
        Document summary
    """
    prompt = f"""Summarize the following financial document in {max_length} words or less.
Focus on key financial data, announcements, and material information.

DOCUMENT:
{document_text[:10000]}  # Limit input to avoid token limits

SUMMARY:
"""
    
    return call_cortex_complete(prompt, model="llama3.1-70b")


@st.cache_data(show_spinner=False, ttl=3600)
def extract_entities(text: str) -> dict:
    """
    Extract financial entities from text using Cortex.
    
    Args:
        text: Text to extract entities from
    
    Returns:
        Dictionary of extracted entities
    """
    prompt = f"""Extract the following entities from this financial text. 
Return as JSON with these keys: companies, tickers, people, monetary_values, dates, metrics.

TEXT:
{text[:5000]}

JSON OUTPUT:
"""
    
    response = call_cortex_complete(prompt, model="llama3.1-70b")
    
    try:
        # Try to parse JSON from response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response[json_start:json_end])
    except json.JSONDecodeError:
        pass
    
    return {"raw_response": response}
