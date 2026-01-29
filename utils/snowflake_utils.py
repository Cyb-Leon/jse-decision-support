"""
Snowflake connection utilities for JSE Decision-Support System.
Handles connection management across different deployment environments.
"""
import streamlit as st


def get_snowflake_session():
    """
    Get Snowflake session based on environment.
    
    Returns:
        Snowpark Session object
    
    Works across:
        - Streamlit in Snowflake (SiS)
        - Local development
        - Streamlit Community Cloud
    """
    # First, check if we're in Streamlit in Snowflake environment
    if is_sis_environment():
        try:
            from snowflake.snowpark.context import get_active_session
            return get_active_session()
        except Exception as e:
            st.error(f"Failed to get SiS session: {e}")
            return None
    
    # Local or Community Cloud - create session from secrets
    try:
        from snowflake.snowpark import Session
        return Session.builder.configs(
            st.secrets["connections"]["snowflake"]
        ).create()
    except Exception as e:
        st.error(f"Failed to establish Snowflake connection: {e}")
        return None


@st.cache_resource
def get_session():
    """
    Cached Snowflake session getter.
    
    Returns:
        Snowpark Session object (cached)
    """
    return get_snowflake_session()


def is_sis_environment() -> bool:
    """
    Detect if running in Streamlit in Snowflake environment.
    
    Returns:
        True if running in SiS, False otherwise
    """
    try:
        import _snowflake
        return True
    except ImportError:
        return False


def execute_query(query: str, params: list = None):
    """
    Execute a SQL query and return results as a Pandas DataFrame.
    
    Args:
        query: SQL query string
        params: Optional list of parameters for parameterized queries
    
    Returns:
        Pandas DataFrame with query results
    """
    session = get_session()
    if session is None:
        return None
    
    try:
        if params:
            result = session.sql(query, params=params)
        else:
            result = session.sql(query)
        return result.to_pandas()
    except Exception as e:
        st.error(f"Query execution failed: {e}")
        return None


def _find_column(df, target_name: str):
    """
    Find a column by name, handling various formats (quoted, unquoted, case variations).
    
    Args:
        df: DataFrame to search
        target_name: Target column name to find
    
    Returns:
        Actual column name in DataFrame, or None if not found
    """
    # Direct match
    if target_name in df.columns:
        return target_name
    
    # Try uppercase
    if target_name.upper() in df.columns:
        return target_name.upper()
    
    # Try lowercase
    if target_name.lower() in df.columns:
        return target_name.lower()
    
    # Handle quoted column names (e.g., '"name"' -> 'name')
    for col in df.columns:
        # Strip quotes and compare
        clean_col = col.strip('"').strip("'").lower()
        if clean_col == target_name.lower():
            return col
    
    return None


def get_available_databases():
    """
    Get list of available databases in Snowflake.
    
    Returns:
        List of database names
    """
    df = execute_query("SHOW DATABASES")
    if df is not None and not df.empty:
        col_name = _find_column(df, "name")
        if col_name is None:
            st.error(f"Could not find 'name' column. Available columns: {list(df.columns)}")
            return []
        return df[col_name].tolist()
    return []


def get_available_schemas(database: str):
    """
    Get list of schemas in a database.
    
    Args:
        database: Database name
    
    Returns:
        List of schema names
    """
    df = execute_query(f"SHOW SCHEMAS IN DATABASE {database}")
    if df is not None and not df.empty:
        col_name = _find_column(df, "name")
        if col_name is None:
            return []
        return df[col_name].tolist()
    return []


def get_available_tables(database: str, schema: str):
    """
    Get list of tables in a schema.
    
    Args:
        database: Database name
        schema: Schema name
    
    Returns:
        List of table names
    """
    df = execute_query(f"SHOW TABLES IN {database}.{schema}")
    if df is not None and not df.empty:
        col_name = _find_column(df, "name")
        if col_name is None:
            return []
        return df[col_name].tolist()
    return []


def table_exists(fully_qualified_name: str) -> bool:
    """
    Check if a table exists.
    
    Args:
        fully_qualified_name: Full table path (database.schema.table)
    
    Returns:
        True if table exists, False otherwise
    """
    try:
        session = get_session()
        session.sql(f"SELECT 1 FROM {fully_qualified_name} LIMIT 1").collect()
        return True
    except:
        return False
