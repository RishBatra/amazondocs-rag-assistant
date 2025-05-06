import os

# File paths Configuration
FILE_PATHS = {
    "test_data": {
        "sample_doc": "tests/test_data/sample_doc.md",
        "test_links": "tests/test_data/test_links.txt",
        "summaries": "tests/test_data/amazon_docs_summary_{}.txt"
    },
    "vector_store": "spapi_vector_index"
}

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "amazondocs_db",
    "user": "postgres", 
    "password": "rb1995"
}

# Model Configuration
EMBEDDING_MODEL_CONFIG = {
    "model_name": "BAAI/bge-large-en-v1.5",  # Better for technical documentation
    "device": "cuda"
}

# Groq API Configuration
GROQ_CONFIG = {
    "api_key": os.environ.get("GROQ_API_KEY"),  # Set your API key as environment variable
    "model": "llama-3.3-70b-versatile",  # Default model
    "temperature": 0.5,
    "max_tokens": 8000,
    "search_min_distance": 1.5,
    "search_limit": 5,
}

# Text Splitting Configuration
TEXT_SPLITTER_CONFIG = {
    "splitter_type": "MarkdownHeaderTextSplitter",
    "chunk_size": 1000,      # Increased for code blocks
    "chunk_overlap": 200,    
    "add_start_index": True, # Add this to track chunk positions
    "length_function": len,  # Add explicit length function
    "separators": [
        "\n## ",            # Markdown h2
        "\n### ",           # Markdown h3
        "\n```\n",          # End of code block
        "\n```json\n",      # Start of JSON block
        "\n```xml\n",       # Start of XML block
        "\n|",              # Table row
        "\n---",            # Table header separator
        "\n\n",             # Paragraphs
        "\n",               # New lines
        ".",                # Sentences
        " ",               # Words
        ""                 # Characters
    ],
    "keep_separator": True,
    "strip_whitespace": False  # Add this to preserve whitespace
}

#URL paths
URL_PATHS = {
    "base_url": "https://developer-docs.amazon.com",
    "api_docs_url": "/sp-api/docs/welcome"
}

#Scraping configuration
SCRAPING_CONFIG = {
    "method": "beautifulsoup",
    "beautifulsoup_settings":{
        "parser": "html.parser",
        "selectors": {
            "content": "article, main, div[role='main']",
            "exclude": "nav, footer, header, script, style"
        }
    }
}

# Search mode configuration
SEARCH_MODE = os.environ.get("SEARCH_MODE", "semantic")  # Options: 'semantic', 'keyword', 'hybrid'

# User-facing messages and prompts
SYSTEM_PROMPT = "You are a helpful assistant for an API documentation. The docdumentation contains API text descriptions, tables and jsons samples for request, response and error codes. Use the provided context to answer as accurately as possible."
NO_RESULTS_MESSAGE = "I couldn't find any relevant information in the documentation to answer your question."
FALLBACK_CONTEXT_MESSAGE = "Based on the documentation, here's what I found: {context}"

# Scrape and process docs limit
SCRAPE_PROCESS_LIMIT = int(os.environ.get("SCRAPE_PROCESS_LIMIT", 10))