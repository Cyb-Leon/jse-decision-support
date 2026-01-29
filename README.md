# JSE Decision-Support System

> **TLDR:** A Streamlit in Snowflake application for analyzing JSE-listed equities, featuring AI-powered research, document analysis (RAG), SENS monitoring, and portfolio tracking.

## Features

- **Dashboard**: Portfolio overview, watchlist management, market summary with sector heatmaps
- **Company Research**: Deep-dive analysis with fundamental metrics, price charts, and AI-generated insights
- **Data Ingestion**: Upload PDFs, CSVs, Excel files; connect to Snowflake tables and external APIs
- **AI Analyst**: RAG-powered chat interface for querying documents and market data using Snowflake Cortex
- **SENS Monitor**: Track JSE announcements with AI summarization and sentiment analysis
- **Settings**: Configure AI models, manage data sources, export/import configurations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
├─────────────────────────────────────────────────────────────┤
│  Dashboard │ Research │ Ingestion │ AI Chat │ SENS │ Settings│
├─────────────────────────────────────────────────────────────┤
│                    Snowflake Backend                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Snowpark   │  │   Cortex    │  │   Cortex Search     │  │
│  │  (Data)     │  │   (LLM)     │  │   (RAG)             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Run Locally

```bash
# Clone the repo
git clone <repo-url>
cd jse-decision-support

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your Snowflake credentials

# Run the app
streamlit run app.py
```

## Deploy to Streamlit in Snowflake

1. Create a Streamlit app in Snowflake:
   ```sql
   CREATE STREAMLIT jse_decision_support
     ROOT_LOCATION = '@my_stage/jse-decision-support'
     MAIN_FILE = 'app.py'
     QUERY_WAREHOUSE = 'COMPUTE_WH';
   ```

2. Upload files to the stage:
   ```sql
   PUT file://app.py @my_stage/jse-decision-support/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file://requirements.txt @my_stage/jse-decision-support/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file://pages/*.py @my_stage/jse-decision-support/pages/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file://utils/*.py @my_stage/jse-decision-support/utils/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   ```

3. Access via Snowflake UI or direct URL

## Project Structure

```
jse-decision-support/
├── app.py                    # Main entry point with navigation
├── pages/
│   ├── dashboard.py          # Portfolio & market overview
│   ├── company_research.py   # Equity deep-dive analysis
│   ├── data_ingestion.py     # Document & data source management
│   ├── ai_analyst.py         # RAG-powered chat interface
│   ├── sens_monitor.py       # JSE announcement tracking
│   └── settings.py           # Configuration & preferences
├── utils/
│   ├── snowflake_utils.py    # Snowflake connection helpers
│   ├── cortex_utils.py       # Cortex LLM utilities
│   └── data_utils.py         # Data processing helpers
├── requirements.txt
├── README.md
└── .streamlit/
    ├── config.toml           # App configuration
    └── secrets.toml.example  # Credentials template
```

## Snowflake Cortex Models

The application uses Snowflake Cortex for AI capabilities:

| Model | Best For |
|-------|----------|
| `claude-3-5-sonnet` | Complex analysis, nuanced reasoning |
| `claude-sonnet-4-5` | Latest Claude model |
| `llama3.1-70b` | General purpose, cost-effective |
| `mistral-large` | Fast responses, good for summaries |

## Data Sources

### Supported Inputs
- **Documents**: PDF annual reports, research notes, filings
- **Spreadsheets**: CSV and Excel files with financial data
- **Snowflake Tables**: Direct connection to existing data
- **APIs**: Configurable connections for market data and news

### RAG Pipeline
Documents are automatically:
1. Parsed and text-extracted
2. Chunked with overlap for context preservation
3. Made available to the AI Analyst for retrieval
4. Cited in AI responses

## Important Notes

- **Not Investment Advice**: This is a decision-support tool, not a recommendation engine
- **No Price Predictions**: The system analyzes data but does not predict prices
- **Data Privacy**: When deployed in SiS, all data stays within Snowflake's security perimeter

## Configuration

### AI Settings
- **Model**: Select from available Cortex models
- **Temperature**: Control response creativity (0.0 - 1.0)
- **Max Tokens**: Limit response length

### Connection
- For SiS: Connection is automatic
- For local: Configure in `.streamlit/secrets.toml`

---

Built with [Streamlit](https://streamlit.io) and [Snowflake Cortex](https://docs.snowflake.com/en/user-guide/snowflake-cortex)
