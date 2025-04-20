from typing import List, Dict, Any, Optional
import json
import re
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
import psycopg2
from psycopg2.extras import Json
from scraper.scraper import get_side_bar_links, scrape_page
import time
import logging
from config import TEXT_SPLITTER_CONFIG
import os

class DocumentProcessor:
    def __init__(self, db_config: Dict[str, str] = None, embedding_model: str = "BAAI/bge-large-en-v1.5"):
        """Initialize the document processor with database and embedding configurations"""
        # Configure logging to only show our custom logs
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename='document_processing.log',
            filemode='w'  # Overwrite the file each time
        )
        
        # Set third-party loggers to a higher level
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('psycopg2').setLevel(logging.WARNING)
        logging.getLogger('huggingface').setLevel(logging.WARNING)
        logging.getLogger('transformers').setLevel(logging.WARNING)
        logging.getLogger('torch').setLevel(logging.WARNING)
        logging.getLogger('tensorflow').setLevel(logging.WARNING)
        logging.getLogger('trafilatura').setLevel(logging.WARNING)
        logging.getLogger('selenium').setLevel(logging.WARNING)
        # Get our logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)  # Keep our logs at DEBUG level
        
        # Load MCP config if db_config not provided
        if db_config is None:
            try:
                with open('mcp.json', 'r') as f:
                    mcp_config = json.load(f)
                db_config = mcp_config['mcpServers']['webscraper-rag-chatbot']
                # Convert MCP config to psycopg2 format
                db_config = {
                    'host': db_config['host'],
                    'port': db_config['port'],
                    'database': db_config['database'],
                    'user': db_config['user'],
                    'password': db_config['password']
                }
            except Exception as e:
                self.logger.error(f"Failed to load MCP config: {str(e)}")
                raise
        
        self.db_config = db_config
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.conn = self._create_db_connection()
        
    def _create_db_connection(self):
        """Create database connection"""
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {str(e)}")
            raise

    def scrape_and_process_docs(self):
        """Scrape documentation and process all pages"""
        # Get all documentation URLs
        urls = get_side_bar_links()
        if not urls:
            print("No URLs found to scrape")
            return
        
        print(f"Found {len(urls)} URLs to process")
        
        # Process each URL
        for url in urls:
            try:
                # Scrape the page
                content = scrape_page(url)
                if not content:
                    print(f"No content found for {url}")
                    continue
                
                # Process the document
                self.process_document(
                    content=content,
                    metadata={
                        'source': url
                    }
                )
                print(f"Successfully processed {url}")
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                continue

    def _extract_json_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Extract JSON blocks from markdown text"""
        json_blocks = []
        json_pattern = r"```\n([\s\S]*?)\n```"
        
        for match in re.finditer(json_pattern, text):
            try:
                json_content = json.loads(match.group(1))
                json_blocks.append({
                    'content': json_content,
                    'position': match.start(),
                    'raw_text': match.group(0)
                })
            except json.JSONDecodeError:
                continue
                
        return json_blocks
    
    def _extract_tables(self, text: str) -> List[Dict[str, Any]]:
        """Extract markdown tables from text"""
        tables = []
        
        # Single pattern to catch all table formats
        table_pattern = r"\|[^\n]+\|\n\|[-:\| ]+\|\n(?:\|?[^\n]+\|\n)+"
        
        for match in re.finditer(table_pattern, text):
            table_text = match.group(0)
            # Call process_table as instance method
            table = self._process_table(table_text)
            if table:
                tables.append(table)
        
        return sorted(tables, key=lambda x: x['position'])

    def _process_table(self, table_text: str) -> Dict[str, Any]:
        """Process a table and return structured data"""
        lines = [line for line in table_text.strip().split('\n') if line.strip()]
        
        # Find the actual table start - look for line with | that's followed by separator
        table_start = 0
        for i in range(len(lines)-1):
            if ('|' in lines[i] and 
                '|' in lines[i+1] and 
                set(lines[i+1].replace('|', '')).issubset({'-', ':', ' '})):
                table_start = i
                break
        
        # Extract only the table lines
        lines = lines[table_start:]
        if len(lines) < 3:  # Need at least header, separator, and one data row
            return None
            
        # Extract headers
        headers = [col.strip() for col in lines[0].split('|')[1:-1]]
        if not headers:  # Skip if no valid headers found
            return None
        
        # Convert table to structured format
        rows = []
        for line in lines[2:]:  # Skip header and separator lines
            # Skip separator lines or empty lines
            if not line.strip() or set(line.replace('|', '')).issubset({'-', ':', ' '}):
                continue
                
            # Handle both cases: with and without leading pipe
            if line.startswith('|'):
                cols = [col.strip() for col in line.split('|')[1:-1]]
            else:
                cols = [col.strip() for col in line.split('|')[:-1]]
            
            if len(cols) == len(headers) and any(col.strip() for col in cols):  # Only add non-empty rows
                rows.append(dict(zip(headers, cols)))
        
        if rows:  # Only return tables that have actual content
            return {
                'headers': headers,
                'content': rows,
                'position': table_text.find(lines[0]),
                'raw_text': '\n'.join(lines)  # Only include actual table lines
            }
        return None

    def process_document(self, content: str, metadata: Dict[str, Any]) -> None:
        """Process a document and store it in the database"""
        try:
            self.logger.debug(f"Processing document from: {metadata.get('source', 'unknown')}")
            self.logger.debug(f"Content length: {len(content)}")
            # # First find and store all matches
            # pattern = r"(`\S+`)\s*(\S+)\s*\1\s*\2"
            # matches = list(re.finditer(pattern, content))
            
            # # First pass: Remove \n\n between first backtick and word
            # for match in matches:
            #     full_match = match.group(0)
            #     backtick_part = match.group(1)
            #     word_part = match.group(2)
            #     # Replace \n\n between backtick and word with a single space
            #     new_first_part = re.sub(r'(`\S+`)\s*\n\n+(\S+)', r'\1 \2', f"{backtick_part}\n\n{word_part}")
            #     content = content.replace(full_match, full_match.replace(f"{backtick_part}\n\n{word_part}", new_first_part))
            
            # # Second pass: Add ### (existing logic)
            # matches = re.finditer(pattern, content)
            # offset = 0
            # for match in Why do you eat like this when you can't say exactly what's typed later it's all inside the domestic air suspensionmatches:
            #     start = match.start() + offset
            #     content = content[:start] + "### " + content[start:]
            #     offset += 4  # Length of "### "
            # Create chunks
            splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[
                    ("#", "Header 1"),
                    ("##", "Header 2"),
                    ("###", "Header 3"),
                ],
                strip_headers=False
            )
            chunks = splitter.split_text(content)

            # Log chunks creation
            # self.logger.debug(f"Created {len(chunks)} chunks")
            # self.logger.debug("=== Chunk Details ===")
            # for i, chunk in enumerate(chunks):
            #     self.logger.debug(f"\nChunk {i+1}:")
            #     self.logger.debug(f"Metadata: {chunk.metadata}")
            #     self.logger.debug(f"Content starts with: {chunk.page_content[:200]}")
            #     self.logger.debug(f"Content length: {len(chunk.page_content)}")
            #     self.logger.debug("=" * 50)
            
            with self.conn.cursor() as cur:
                # Track the current section headers and their IDs
                current_h1 = {'id': None, 'title': None}
                current_h2 = {'id': None, 'title': None}
                
                for i, chunk in enumerate(chunks):
                    # Determine header level and content from metadata
                    current_level = 0
                    h1_title = chunk.metadata.get("Header 1")
                    h2_title = chunk.metadata.get("Header 2")
                    h3_title = chunk.metadata.get("Header 3")
                    
                    if h3_title:
                        current_level = 3
                    elif h2_title:
                        current_level = 2
                    elif h1_title:
                        current_level = 1
                    
                    # If we have an H3 with a new H2 section, create the H2 node first
                    if current_level == 3 and h2_title and (current_h2['title'] != h2_title):
                        # Create H2 node
                        h2_metadata = {
                            "Header 1": h1_title,
                            "Header 2": h2_title
                        }
                        
                        cur.execute("""
                            INSERT INTO document_chunks (parent_id, content, embedding, metadata)
                            VALUES (%s, %s, %s, %s)
                            RETURNING id
                        """, (
                            current_h1['id'],  # Parent is current H1
                            f"## {h2_title}",  # Content is the header itself
                            self.embeddings.embed_query(h2_title),
                            Json(h2_metadata)
                        ))
                        
                        result = cur.fetchone()
                        current_h2['id'] = result[0]
                        current_h2['title'] = h2_title
                    
                    # Get parent_id based on header level
                    parent_id = None
                    
                    if current_level == 1:
                        # H1 headers have no parent
                        parent_id = None
                        # Update current H1 and reset H2
                        current_h1['title'] = h1_title
                        current_h2 = {'id': None, 'title': None}
                    elif current_level == 2:
                        # H2 headers are children of current H1
                        parent_id = current_h1['id']
                        # Update current H2
                        current_h2['title'] = h2_title
                    elif current_level == 3:
                        # H3 headers are children of current H2 if it exists
                        if current_h2['id'] is not None and h2_title == current_h2['title']:
                            parent_id = current_h2['id']
                        else:
                            parent_id = current_h1['id']
                    
                    # Extract JSON and tables first and add chunk metadata to them
                    json_blocks = [
                        {**block, 'metadata': chunk.metadata} 
                        for block in self._extract_json_blocks(chunk.page_content)
                    ]
                    tables = [
                        {**block, 'metadata': chunk.metadata} 
                        for block in self._extract_tables(chunk.page_content)
                    ]
                    
                    # Remove JSON and tables from text for chunking
                    clean_text = chunk.page_content
                    for block in json_blocks + tables:
                        clean_text = clean_text.replace(block['raw_text'], '[EXTRACTED_CONTENT]')
                    
                    # Generate embedding for the chunk
                    embedding = self.embeddings.embed_query(clean_text)
                    
                    # Insert the chunk and get its ID
                    cur.execute("""
                        INSERT INTO document_chunks (parent_id, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (
                        parent_id,
                        clean_text,
                        embedding,
                        Json(chunk.metadata)
                    ))
                    
                    result = cur.fetchone()
                    chunk_id = result[0]
                    
                    # Update the current section IDs
                    if current_level == 1:
                        current_h1['id'] = chunk_id
                    elif current_level == 2:
                        current_h2['id'] = chunk_id
                    
                    # Store associated JSON blocks
                    for json_block in json_blocks:
                        if '[EXTRACTED_CONTENT]' in clean_text:
                            cur.execute("""
                                INSERT INTO json_blocks (chunk_id, json_content, metadata)
                                VALUES (%s, %s, %s)
                            """, (
                                chunk_id, 
                                Json(json_block['content']), 
                                Json(json_block['metadata'])  # Use Json adapter for metadata
                            ))

                    # Store associated tables
                    for table in tables:
                        if '[EXTRACTED_CONTENT]' in clean_text:
                            cur.execute("""
                                INSERT INTO table_blocks (chunk_id, table_content, headers, metadata)
                                VALUES (%s, %s, %s, %s)
                            """, (
                                chunk_id,
                                Json(table['content']),
                                table['headers'],
                                Json(table['metadata'])  # Use Json adapter for metadata
                            ))
                    self.conn.commit()

            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Error processing document: {str(e)}", exc_info=True)
            self.conn.rollback()  # Rollback on error
            raise

    def search(self, query: str, limit: int = 3, min_distance: float = 0.8) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        query_embedding = self.embeddings.embed_query(query)
        
        with self.conn.cursor() as cur:
            # Search for relevant chunks using vector similarity
            cur.execute("""
                SELECT id, content, metadata,
                       embedding <-> %s::vector(1024) as distance
                FROM document_chunks
                WHERE embedding <-> %s::vector(1024) < %s
                ORDER BY distance
                LIMIT %s
            """, (query_embedding, query_embedding, min_distance, limit))
            
            results = []
            for row in cur.fetchall():
                chunk_id, content, metadata, distance = row
                
                # Get associated JSON blocks
                cur.execute("SELECT json_content FROM json_blocks WHERE chunk_id = %s", (chunk_id,))
                json_blocks = [r[0] for r in cur.fetchall()]
                
                # Get associated tables
                cur.execute("SELECT table_content, headers FROM table_blocks WHERE chunk_id = %s", (chunk_id,))
                tables = [{"content": r[0], "headers": r[1]} for r in cur.fetchall()]
                
                results.append({
                    "content": content,
                    "metadata": metadata,
                    "json_blocks": json_blocks,
                    "tables": tables,
                    "distance": distance
                })
                
            return results

    def close(self):
        """Close database connection"""
        self.conn.close()

    def test_database_connection(self):
        """Test database operations"""
        try:
            with self.conn.cursor() as cur:
                # Test insert
                cur.execute("""
                    INSERT INTO document_chunks (title, content, embedding)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (
                    'test_title',
                    'test_content',
                    [0.1] * 1024  # Test embedding
                ))
                
                result = cur.fetchone()
                self.logger.debug(f"Test insert result: {result}")
                
                # Rollback test data
                self.conn.rollback()
                return True
                
        except Exception as e:
            self.logger.error(f"Database test failed: {str(e)}", exc_info=True)
            return False

    def setup_database(self):
        """Set up database schema with correct vector dimensions"""
        try:
            with self.conn.cursor() as cur:
                # Enable vector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Drop existing table if it exists
                cur.execute("DROP TABLE IF EXISTS table_blocks;")
                cur.execute("DROP TABLE IF EXISTS json_blocks;")
                cur.execute("DROP TABLE IF EXISTS document_chunks;")
                
                # Create document_chunks table with 1024-dimensional vector
                cur.execute("""
                    CREATE TABLE document_chunks (
                        id SERIAL PRIMARY KEY,
                        parent_id INTEGER REFERENCES document_chunks(id),
                        title TEXT,
                        content TEXT,
                        embedding vector(1024),
                        metadata JSONB
                    );
                """)
                
                # Create other tables
                cur.execute("""
                    CREATE TABLE json_blocks (
                        id SERIAL PRIMARY KEY,
                        chunk_id INTEGER REFERENCES document_chunks(id),
                        json_content JSONB,
                        metadata JSONB
                    );
                """)
                
                # Create table_blocks table without created_at
                cur.execute("""
                    CREATE TABLE table_blocks (
                        id SERIAL PRIMARY KEY,
                        chunk_id INTEGER REFERENCES document_chunks(id),
                        table_content JSONB,
                        headers TEXT[],
                        metadata JSONB
                    );
                """)
                
                # Create index for similarity search
                cur.execute("""
                    CREATE INDEX ON document_chunks 
                    USING ivfflat (embedding vector_l2_ops);
                """)
                
                self.conn.commit()
                self.logger.info("Database schema created successfully")
                return True
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Failed to set up database: {str(e)}", exc_info=True)
            return False 