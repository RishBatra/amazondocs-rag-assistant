# Amazon API Documentation Chatbot 🤖

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Retrieval-Augmented Generation (RAG) chatbot for Amazon API documentation that provides accurate answers to user queries by scraping, processing, and retrieving relevant Amazon API documentation.

<p align="center">
  <img src="https://user-images.githubusercontent.com/your-username/your-repo/assets/your-asset-id/chatbot-example.png" alt="Chatbot Example" width="600">
</p>

## 📋 Table of Contents

- [Overview](#-overview)
- [Components](#-components)
- [Setup](#-setup)
- [Usage](#-usage)
- [Search Modes](#-search-modes)
- [Technology Stack](#-technology-stack)

## 🔍 Overview

This project creates an intelligent chatbot that:

1. Scrapes Amazon API documentation pages
2. Processes and stores the documentation with embeddings in a PostgreSQL database 
3. Retrieves relevant documentation based on user queries
4. Generates accurate responses using LLMs (via Groq)

## 🧩 Components

### 🕸️ Web Scraper (`scraper/scraper.py`)
- Extracts documentation from Amazon developer pages
- Collects navigation links from sidebars
- Converts HTML content to Markdown format
- Preserves tables, code blocks, and other structured content

### 📊 Document Processor (`processor/document_processor.py`)
- Processes Markdown text and extracts structured data
- Identifies and extracts tables and JSON code blocks:
    - JSON blocks are stored in a separate `json_blocks` table, linked to document chunks via `chunk_id`. Stores `json_content` (JSONB) and `metadata`.
    - Markdown tables are stored in a separate `table_blocks` table, linked to document chunks via `chunk_id`. Stores `table_content` (JSONB for rows), `headers` (TEXT[]), and `metadata`.
- Uses `BAAI/bge-large-en-v1.5` for generating embeddings for semantic search
- Implements a chunking strategy based on Markdown headers (H1, H2, H3) using `MarkdownHeaderTextSplitter`, preserving header content within chunks.
- Stores main document content in `document_chunks` table with a hierarchical structure (parent-child relationships for headers).
- Supports various search modes (semantic, keyword, hybrid)

### 🔎 Query Handler (`query_handler.py`)
- Handles user queries and retrieves relevant documentation
- Uses embeddings for semantic search
- Formats search results into context for LLM generation
- Interfaces with Groq API for generating responses

### 💬 CLI Interface (`chat_cli.py`)
- Provides a simple command-line interface for the chatbot
- Maintains conversation context for follow-up questions
- Clarifies ambiguous queries using previous context

## 🛠️ Setup

### Prerequisites
- Python 3.7+
- PostgreSQL database with vector extension
- Groq API key

### Installation

Install required Python libraries:

```bash
pip install langchain langchain_community huggingface_hub psycopg2-binary 
pip install transformers torch
pip install trafilatura selenium beautifulsoup4 requests
pip install groq
```

Or install from requirements file:

```bash
pip install -r requirements.txt
```

Content for `requirements.txt`:
```
langchain
langchain_community
huggingface_hub
psycopg2-binary
transformers
torch
trafilatura
selenium
beautifulsoup4
requests
groq
```

### Environment Variables

Create a `.env` file with the following variables:

```
DB_HOST=your_db_host
DB_PORT=your_db_port
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
GROQ_API_KEY=your_groq_api_key
SEARCH_MODE=hybrid  # Options: semantic, keyword, hybrid
SCRAPE_PROCESS_LIMIT=10  # Limit for scraping in initial setup
```

### Database Setup

The system requires a PostgreSQL database with the vector extension installed. The `DocumentProcessor.setup_database()` method creates the necessary tables:

| Table | Description |
|-------|-------------|
| `document_chunks` | Stores document content with embeddings |
| `json_blocks` | Stores JSON examples extracted from documentation |
| `table_blocks` | Stores table data extracted from documentation |

## 🚀 Usage

1. Set up environment variables in `.env` file

2. Initialize the database:

```python
from processor.document_processor import DocumentProcessor
from config import DB_CONFIG

# Create the database schema
processor = DocumentProcessor(DB_CONFIG)
processor.setup_database()
```

3. Scrape and process documentation:

```python
# Limit the number of pages to process
processor.scrape_and_process_docs(limit=10)
```

4. Run the CLI chatbot:

```bash
python chat_cli.py
```

Example conversation:
```
Amazon Docs Chatbot (type 'exit' or 'quit' to end)
You: How do I authenticate with the Amazon SP-API?
AI: To authenticate with Amazon's Selling Partner API (SP-API), you need to follow these steps:

1. Create LWA (Login with Amazon) credentials
2. Generate a refresh token
3. Make API calls using the LWA tokens

[Further details about authentication would appear here...]

You: What are the rate limits?
AI: [Response about rate limits...]
```

## 🔄 Search Modes

The system supports three search modes:

| Mode | Description |
|------|-------------|
| **Semantic** | Uses vector embeddings for semantic similarity search |
| **Keyword** | Uses text matching for keyword search |
| **Hybrid** | Combines both semantic and keyword search for comprehensive results |

## 💻 Technology Stack

- **Web Scraping**: Trafilatura, Selenium, BeautifulSoup
- **Embeddings**: HuggingFace models (BAAI/bge-large-en-v1.5)
- **Database**: PostgreSQL with vector extension
- **LLM Integration**: Groq API (llama-3.3-70b-versatile)
- **Text Processing**: Regular expressions, Markdown parsing

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- Amazon Developer Documentation
- Hugging Face for open-source models 