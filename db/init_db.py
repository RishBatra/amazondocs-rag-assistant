import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config import DB_CONFIG

def init_database(config):
    """Initialize the database and create required tables"""
    
    # Connect to PostgreSQL server
    conn = psycopg2.connect(
        host=config['host'],
        user=config['user'],
        password=config['password']
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    # Create database if it doesn't exist
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config['dbname'],))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {config['dbname']}")
    
    conn.close()
    
    # Connect to the new database
    conn = psycopg2.connect(**config)
    
    with conn.cursor() as cur:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Create document_chunks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                parent_id INTEGER REFERENCES document_chunks(id),
                title TEXT,
                content TEXT,
                embedding vector(1024),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create json_blocks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS json_blocks (
                id SERIAL PRIMARY KEY,
                chunk_id INTEGER REFERENCES document_chunks(id),
                json_content JSONB,
                description TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create table_blocks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS table_blocks (
                id SERIAL PRIMARY KEY,
                chunk_id INTEGER REFERENCES document_chunks(id),
                table_content JSONB,
                headers TEXT[],
                description TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vector similarity search index
        cur.execute("""
            CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
            ON document_chunks 
            USING ivfflat (embedding vector_cosine_ops)
        """)
        
    conn.commit()
    conn.close() 