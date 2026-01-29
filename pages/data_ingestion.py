"""
Data Ingestion Page - Upload documents, configure APIs, manage data sources.
JSE Decision-Support System
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json

import sys
sys.path.append("..")
from utils.data_utils import (
    parse_csv_upload,
    parse_excel_upload,
    extract_text_from_pdf,
    chunk_text,
)
from utils.cortex_utils import summarize_document, extract_entities
from utils.snowflake_utils import (
    get_session,
    execute_query,
    get_available_databases,
    get_available_schemas,
    get_available_tables,
)


def render_document_upload():
    """Render document upload section."""
    st.subheader(":material/upload_file: Document Upload")
    st.caption("Upload PDFs, CSVs, or Excel files for analysis")
    
    companies = st.session_state.get("companies", [])
    
    # Company selection for document association
    if companies:
        company_options = ["None (General)"] + [f"{c['ticker']} - {c['name']}" for c in companies]
        selected_company_display = st.selectbox(
            "Associate with company (optional)",
            options=company_options,
            key="doc_company_select",
            help="Link this document to a specific company for focused analysis",
        )
        
        if selected_company_display != "None (General)":
            selected_ticker = selected_company_display.split(" - ")[0]
        else:
            selected_ticker = None
    else:
        selected_ticker = None
        st.info("Add companies in the Dashboard to associate documents with them.")
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=["pdf", "csv", "xlsx", "xls", "txt"],
        accept_multiple_files=True,
        key="doc_uploader"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_type = uploaded_file.name.split(".")[-1].lower()
            
            with st.expander(f":material/description: {uploaded_file.name}", expanded=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.caption(f"Type: {file_type.upper()} | Size: {uploaded_file.size / 1024:.1f} KB")
                    if selected_ticker:
                        st.caption(f":material/link: Associated with: {selected_ticker}")
                
                with col2:
                    process_btn = st.button(
                        ":material/auto_awesome: Process",
                        key=f"process_{uploaded_file.name}",
                        use_container_width=True
                    )
                
                if process_btn:
                    with st.status("Processing document...", expanded=True) as status:
                        doc_data = {
                            "name": uploaded_file.name,
                            "type": file_type,
                            "size": uploaded_file.size,
                            "uploaded_at": datetime.now().isoformat(),
                            "ticker": selected_ticker,  # Associate with company
                        }
                        
                        # Process based on file type
                        if file_type == "pdf":
                            st.write(":material/description: Extracting text from PDF...")
                            text = extract_text_from_pdf(uploaded_file)
                            if text:
                                doc_data["content"] = text
                                doc_data["chunks"] = chunk_text(text)
                                st.write(f":material/check: Extracted {len(text)} characters")
                                st.write(f":material/check: Created {len(doc_data['chunks'])} chunks for RAG")
                                
                                # Summarize
                                st.write(":material/psychology: Generating summary...")
                                doc_data["summary"] = summarize_document(text[:8000])
                                
                        elif file_type == "csv":
                            st.write(":material/table_chart: Parsing CSV...")
                            df = parse_csv_upload(uploaded_file)
                            if df is not None:
                                doc_data["dataframe"] = df.to_dict()
                                doc_data["columns"] = list(df.columns)
                                doc_data["rows"] = len(df)
                                st.write(f":material/check: Loaded {len(df)} rows, {len(df.columns)} columns")
                                st.dataframe(df.head(), use_container_width=True)
                                
                        elif file_type in ["xlsx", "xls"]:
                            st.write(":material/table_chart: Parsing Excel...")
                            sheets = parse_excel_upload(uploaded_file)
                            if sheets:
                                doc_data["sheets"] = {k: v.to_dict() for k, v in sheets.items()}
                                doc_data["sheet_names"] = list(sheets.keys())
                                st.write(f":material/check: Loaded {len(sheets)} sheets")
                                for sheet_name, df in sheets.items():
                                    st.caption(f"Sheet: {sheet_name} ({len(df)} rows)")
                                    
                        elif file_type == "txt":
                            st.write(":material/description: Reading text file...")
                            text = uploaded_file.read().decode("utf-8")
                            doc_data["content"] = text
                            doc_data["chunks"] = chunk_text(text)
                            st.write(f":material/check: Loaded {len(text)} characters")
                        
                        # Add to session state
                        st.session_state.uploaded_documents.append(doc_data)
                        st.session_state.ingested_sources.append({
                            "type": "document",
                            "name": uploaded_file.name,
                            "timestamp": datetime.now().isoformat(),
                        })
                        
                        status.update(label="Document processed!", state="complete")
                        st.success(f"Added {uploaded_file.name} to knowledge base")


def render_snowflake_connection():
    """Render Snowflake data source configuration."""
    st.subheader(":material/database: Snowflake Tables")
    st.caption("Connect to existing Snowflake tables")
    
    session = get_session()
    
    if session:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            databases = get_available_databases()
            selected_db = st.selectbox(
                "Database",
                options=databases if databases else ["No databases available"],
                key="sf_database_select"
            )
        
        with col2:
            if selected_db and selected_db != "No databases available":
                schemas = get_available_schemas(selected_db)
                selected_schema = st.selectbox(
                    "Schema",
                    options=schemas if schemas else ["No schemas available"],
                    key="sf_schema_select"
                )
            else:
                selected_schema = st.selectbox("Schema", options=["Select database first"], key="sf_schema_select")
        
        with col3:
            if selected_schema and selected_schema not in ["No schemas available", "Select database first"]:
                tables = get_available_tables(selected_db, selected_schema)
                selected_table = st.selectbox(
                    "Table",
                    options=tables if tables else ["No tables available"],
                    key="sf_table_select"
                )
            else:
                selected_table = st.selectbox("Table", options=["Select schema first"], key="sf_table_select")
        
        if st.button(":material/link: Connect Table", use_container_width=True):
            if selected_table not in ["No tables available", "Select schema first"]:
                full_path = f"{selected_db}.{selected_schema}.{selected_table}"
                
                with st.spinner("Connecting to table..."):
                    # Preview the table
                    preview_df = execute_query(f"SELECT * FROM {full_path} LIMIT 100")
                    
                    if preview_df is not None:
                        st.success(f"Connected to {full_path}")
                        st.dataframe(preview_df.head(10), use_container_width=True)
                        
                        # Add to ingested sources
                        st.session_state.ingested_sources.append({
                            "type": "snowflake_table",
                            "name": full_path,
                            "timestamp": datetime.now().isoformat(),
                            "columns": list(preview_df.columns),
                            "row_count": len(preview_df),
                        })
                    else:
                        st.error("Failed to connect to table")
    else:
        st.warning("Snowflake session not available. Check your connection settings.")
        
        with st.expander(":material/settings: Manual Connection"):
            st.text_input("Account", key="manual_account")
            st.text_input("User", key="manual_user")
            st.text_input("Password", type="password", key="manual_password")
            st.text_input("Warehouse", key="manual_warehouse")
            st.text_input("Database", key="manual_database")
            st.text_input("Schema", key="manual_schema")
            
            if st.button(":material/link: Connect"):
                st.info("Connection will be established on next page load")


def render_api_connections():
    """Render API connection configuration."""
    st.subheader(":material/api: External APIs")
    st.caption("Configure connections to market data and news APIs")
    
    api_options = [
        {
            "name": "JSE Market Data",
            "description": "Real-time and historical JSE price data",
            "fields": ["API Key", "Base URL"],
        },
        {
            "name": "News API",
            "description": "Financial news and SENS announcements",
            "fields": ["API Key"],
        },
        {
            "name": "Company Filings",
            "description": "Annual reports and regulatory filings",
            "fields": ["API Key", "Subscription Tier"],
        },
        {
            "name": "Economic Data",
            "description": "Macro indicators and economic calendar",
            "fields": ["API Key"],
        },
    ]
    
    for api in api_options:
        with st.expander(f":material/api: {api['name']}", expanded=False):
            st.caption(api["description"])
            
            api_config = {}
            for field in api["fields"]:
                api_config[field] = st.text_input(
                    field,
                    type="password" if "Key" in field else "default",
                    key=f"api_{api['name']}_{field}"
                )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(":material/link: Connect", key=f"connect_{api['name']}", use_container_width=True):
                    # Store API configuration
                    st.session_state.api_connections[api["name"]] = {
                        "config": api_config,
                        "connected_at": datetime.now().isoformat(),
                        "status": "connected",
                    }
                    st.success(f"Connected to {api['name']}")
            
            with col2:
                if api["name"] in st.session_state.api_connections:
                    if st.button(":material/link_off: Disconnect", key=f"disconnect_{api['name']}", use_container_width=True):
                        del st.session_state.api_connections[api["name"]]
                        st.rerun()
            
            # Show connection status
            if api["name"] in st.session_state.api_connections:
                st.success(f"Status: Connected")


def render_data_sources_overview():
    """Render overview of all connected data sources."""
    st.subheader(":material/folder: Connected Data Sources")
    
    if not st.session_state.ingested_sources and not st.session_state.api_connections:
        st.info("No data sources connected yet. Add documents, tables, or APIs above.")
        return
    
    # Documents
    if st.session_state.uploaded_documents:
        st.markdown("**Documents**")
        for doc in st.session_state.uploaded_documents:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.caption(f":material/description: {doc['name']}")
            with col2:
                st.caption(doc.get('type', 'Unknown').upper())
            with col3:
                if st.button(":material/delete:", key=f"del_doc_{doc['name']}", help="Remove"):
                    st.session_state.uploaded_documents.remove(doc)
                    st.rerun()
    
    # Snowflake Tables
    sf_sources = [s for s in st.session_state.ingested_sources if s["type"] == "snowflake_table"]
    if sf_sources:
        st.markdown("**Snowflake Tables**")
        for source in sf_sources:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.caption(f":material/database: {source['name']}")
            with col2:
                st.caption(f"{source.get('row_count', '?')} rows")
            with col3:
                if st.button(":material/delete:", key=f"del_sf_{source['name']}", help="Remove"):
                    st.session_state.ingested_sources.remove(source)
                    st.rerun()
    
    # APIs
    if st.session_state.api_connections:
        st.markdown("**API Connections**")
        for api_name, api_info in st.session_state.api_connections.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.caption(f":material/api: {api_name}")
            with col2:
                st.caption(api_info.get("status", "Unknown"))
            with col3:
                if st.button(":material/delete:", key=f"del_api_{api_name}", help="Remove"):
                    del st.session_state.api_connections[api_name]
                    st.rerun()


def render_bulk_import():
    """Render bulk import section."""
    st.subheader(":material/cloud_upload: Bulk Import")
    st.caption("Import multiple documents or data files at once")
    
    with st.expander(":material/info: Import Tips"):
        st.markdown("""
        **Supported formats:**
        - **PDF**: Annual reports, research notes, filings
        - **CSV**: Price data, financial metrics, portfolio holdings
        - **Excel**: Multi-sheet workbooks with financial data
        - **TXT**: News articles, analyst notes
        
        **Best practices:**
        - Name files with ticker symbols for auto-tagging (e.g., `NPN_Annual_Report_2024.pdf`)
        - Use consistent date formats in CSV files
        - Keep individual files under 50MB for optimal processing
        """)
    
    # Bulk upload
    bulk_files = st.file_uploader(
        "Drop multiple files here",
        type=["pdf", "csv", "xlsx", "txt"],
        accept_multiple_files=True,
        key="bulk_uploader"
    )
    
    if bulk_files:
        st.write(f"**{len(bulk_files)} files selected**")
        
        if st.button(":material/play_arrow: Process All", type="primary", use_container_width=True):
            progress = st.progress(0)
            status_text = st.empty()
            
            for i, file in enumerate(bulk_files):
                status_text.text(f"Processing {file.name}...")
                
                # Similar processing logic as single upload
                file_type = file.name.split(".")[-1].lower()
                doc_data = {
                    "name": file.name,
                    "type": file_type,
                    "size": file.size,
                    "uploaded_at": datetime.now().isoformat(),
                }
                
                if file_type == "pdf":
                    text = extract_text_from_pdf(file)
                    if text:
                        doc_data["content"] = text
                        doc_data["chunks"] = chunk_text(text)
                elif file_type == "csv":
                    df = parse_csv_upload(file)
                    if df is not None:
                        doc_data["dataframe"] = df.to_dict()
                        doc_data["columns"] = list(df.columns)
                elif file_type in ["xlsx", "xls"]:
                    sheets = parse_excel_upload(file)
                    if sheets:
                        doc_data["sheets"] = {k: v.to_dict() for k, v in sheets.items()}
                elif file_type == "txt":
                    text = file.read().decode("utf-8")
                    doc_data["content"] = text
                    doc_data["chunks"] = chunk_text(text)
                
                st.session_state.uploaded_documents.append(doc_data)
                progress.progress((i + 1) / len(bulk_files))
            
            progress.empty()
            status_text.empty()
            st.success(f"Processed {len(bulk_files)} files!")


# Main page rendering
st.title(":material/upload_file: Data Ingestion")
st.caption("Connect and manage your data sources")

# Tabs for different ingestion methods
tab1, tab2, tab3, tab4 = st.tabs([
    ":material/description: Documents",
    ":material/database: Snowflake",
    ":material/api: APIs",
    ":material/cloud_upload: Bulk Import"
])

with tab1:
    render_document_upload()

with tab2:
    render_snowflake_connection()

with tab3:
    render_api_connections()

with tab4:
    render_bulk_import()

st.divider()
render_data_sources_overview()

# Sidebar with data stats
with st.sidebar:
    st.header(":material/analytics: Data Statistics")
    
    total_docs = len(st.session_state.uploaded_documents)
    total_tables = len([s for s in st.session_state.ingested_sources if s["type"] == "snowflake_table"])
    total_apis = len(st.session_state.api_connections)
    
    st.metric("Documents", total_docs)
    st.metric("Snowflake Tables", total_tables)
    st.metric("API Connections", total_apis)
    
    st.divider()
    
    if st.button(":material/delete_forever: Clear All Sources", use_container_width=True):
        st.session_state.uploaded_documents = []
        st.session_state.ingested_sources = []
        st.session_state.api_connections = {}
        st.rerun()
