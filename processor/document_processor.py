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

class DocumentProcessor:
    def __init__(self, db_config: Dict[str, str], embedding_model: str = "BAAI/bge-large-en-v1.5"):
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
        
        self.db_config = db_config
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.conn = self._create_db_connection()
        
    def _create_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_config)

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
                        'source': url,
                        'type': 'api_documentation',
                        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
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
            self.logger.debug(f"Created {len(chunks)} chunks")
            
            with self.conn.cursor() as cur:
                parent_id = None
                current_level = 0
                
                for i, chunk in enumerate(chunks):
                    self.logger.debug(f"Processing chunk {i+1}/{len(chunks)}")
                    self.logger.debug(f"Chunk level: {chunk.metadata.get('level')}")
                    self.logger.debug(f"Parent ID: {parent_id}")

                    # Extract JSON and tables first
                    json_blocks = self._extract_json_blocks(chunk.page_content)
                    tables = self._extract_tables(chunk.page_content)
                    
                    # Remove JSON and tables from text for chunking
                    clean_text = chunk.page_content
                    for block in json_blocks + tables:
                        clean_text = clean_text.replace(block['raw_text'], '[EXTRACTED_CONTENT]')
                    
                    # Generate embedding for the chunk
                    embedding = self.embeddings.embed_query(clean_text)
                    
                    # Now use the embedding in the insert
                    cur.execute("""
                        INSERT INTO document_chunks (parent_id, title, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        parent_id,
                        chunk.metadata.get('title', ''),
                        chunk.page_content,
                        embedding,
                        Json(metadata)
                    ))
                    
                    result = cur.fetchone()
                    self.logger.debug(f"Insert result: {result}")
                    
                    chunk_id = result[0]
                    current_level = int(chunk.metadata.get('level', 1))
                    if current_level > current_level:
                        parent_id = chunk_id
                    elif current_level < current_level:
                        # TODO: Implement logic to find correct parent
                        pass
                    
                    # Store associated JSON blocks
                    for json_block in json_blocks:
                        if '[EXTRACTED_CONTENT]' in chunk.page_content:
                            cur.execute("""
                                INSERT INTO json_blocks (chunk_id, json_content, metadata)
                                VALUES (%s, %s, %s)
                            """, (chunk_id, Json(json_block['content']), Json(metadata)))

                    # Store associated tables
                    for table in tables:
                        if '[EXTRACTED_CONTENT]' in chunk.page_content:
                            cur.execute("""
                                INSERT INTO table_blocks (chunk_id, table_content, headers, metadata)
                                VALUES (%s, %s, %s, %s)
                            """, (
                                chunk_id,
                                Json(table['content']),
                                table['headers'],
                                Json(metadata)
                            ))

            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Error processing document: {str(e)}", exc_info=True)
            raise

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        query_embedding = self.embeddings.embed_query(query)
        
        with self.conn.cursor() as cur:
            # Search for relevant chunks
            cur.execute("""
                SELECT id, content, metadata,
                       embedding <-> %s as distance
                FROM document_chunks
                ORDER BY distance
                LIMIT %s
            """, (query_embedding, limit))
            
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
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create other tables
                cur.execute("""
                    CREATE TABLE json_blocks (
                        id SERIAL PRIMARY KEY,
                        chunk_id INTEGER REFERENCES document_chunks(id),
                        json_content JSONB,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE table_blocks (
                        id SERIAL PRIMARY KEY,
                        chunk_id INTEGER REFERENCES document_chunks(id),
                        table_content JSONB,
                        headers TEXT[],
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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