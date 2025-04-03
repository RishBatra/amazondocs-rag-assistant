# Document Processing and Storage Design

## Overview
This document outlines the design for processing and storing documentation that contains text, JSON schemas, and tables using PostgreSQL with pgvector extension. The design enables efficient semantic search while preserving the exact structure of JSON schemas and tables.

## Database Schema

### Document Chunks Table
The main table for storing text content with vector embeddings:

```sql
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES document_chunks(id),
    title TEXT,
    content TEXT,
    embedding vector(1024),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- `parent_id`: Enables hierarchical relationships between chunks
- `embedding`: Stores vector embeddings for semantic search
- `metadata`: Stores additional information like source, position, etc.

### JSON Blocks Table
Dedicated table for storing JSON content:

```sql
CREATE TABLE json_blocks (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES document_chunks(id),
    json_content JSONB,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table Blocks Table
Dedicated table for storing table content:

```sql
CREATE TABLE table_blocks (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES document_chunks(id),
    table_content JSONB,
    headers TEXT[],
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Chunking Strategy

### Rules for Chunking
1. Create a new chunk when:
   - Encountering a new header (#, ##, ###)
   - Reaching maximum token limit
   - Before and after JSON blocks or tables

2. Maintain hierarchy:
   - Level 1 headers (#) create parent chunks
   - Level 2 headers (##) create child chunks
   - Level 3 headers (###) create grandchild chunks

3. Special content handling:
   - JSON blocks are stored separately with reference to parent chunk
   - Tables are stored separately with reference to parent chunk
   - Code blocks remain with their context in the main chunk

### Example Document Structure 