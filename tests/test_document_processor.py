import unittest
from unittest.mock import Mock, patch
import json
import logging
from processor.document_processor import DocumentProcessor
from scraper.scraper import scrape_page
from config import DB_CONFIG, URL_PATHS

class TestDocumentProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before all tests."""
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.logger.info("Setting up test...")
        self.db_config = DB_CONFIG
        self.processor = DocumentProcessor(self.db_config)
        
    def tearDown(self):
        """Clean up after each test method."""
        self.logger.info("Tearing down test...")
        if hasattr(self, 'processor'):
            self.processor.close()

    def test_extract_tables(self):
        """Test table extraction from markdown text."""
        test_markdown = """
        | Header1 | Header2 |
        |---------|---------|
        | Value1  | Value2  |
        | Value3  | Value4  |
        """
        tables = self.processor._extract_tables(test_markdown)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]['headers'], ['Header1', 'Header2'])
        self.assertEqual(len(tables[0]['content']), 2)

    def test_extract_json_blocks(self):
        """Test JSON block extraction from markdown text."""
        test_markdown = """
        Some text
        ```
        {"key": "value"}
        ```
        More text
        """
        json_blocks = self.processor._extract_json_blocks(test_markdown)
        self.assertEqual(len(json_blocks), 1)
        self.assertEqual(json_blocks[0]['content'], {"key": "value"})

    @patch('processor.document_processor.HuggingFaceEmbeddings')
    def test_process_document_with_mock_data(self, mock_embeddings):
        """Test document processing with mock data."""
        mock_embeddings.return_value.embed_query.return_value = [0.1] * 1024
        
        test_content = """
        # Header 1
        | Column1 | Column2 |
        |---------|---------|
        | Data1   | Data2   |
        
        ```
        {"test": "data"}
        ```
        """
        
        test_metadata = {
            'source': 'test_url'
        }
        
        try:
            self.processor.process_document(test_content, test_metadata)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"process_document raised an exception: {str(e)}")

    @patch('processor.document_processor.HuggingFaceEmbeddings')
    def test_process_document_with_scraper(self, mock_embeddings):
        """Test document processing with real scraping."""
        mock_embeddings.return_value.embed_query.return_value = [0.1] * 1024
        
        # Use a test URL from your API docs
        test_url = "https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-use-case-guide"
        # test_url = "https://developer-docs.amazon.com/sp-api/docs/messaging-api-v1-reference"
        # test_url = "https://developer-docs.amazon.com/sp-api/docs/sales-api-v1-use-case-guide"
        
        
        # Scrape the content
        content = scrape_page(test_url)
        self.assertIsNotNone(content, "Failed to scrape content from URL")
        
        test_metadata = {
            'source': test_url
        }
        
        try:
            self.processor.process_document(content, test_metadata)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"process_document with scraped content raised an exception: {str(e)}")

    def test_database_connection(self):
        """Test database operations"""
        try:
            with self.conn.cursor() as cur:
                # Test insert
                cur.execute("""
                    INSERT INTO document_chunks (content, embedding, metadata)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (
                    'test_content',
                    [0.1] * 1024,  # Test embedding
                    json.dumps({'test': 'metadata'})
                ))
                
                result = cur.fetchone()
                self.logger.debug(f"Test insert result: {result}")
                
                # Rollback test data
                self.conn.rollback()
                return True
                
        except Exception as e:
            self.logger.error(f"Database test failed: {str(e)}")
            return False

    def test_search(self):
        """Test search functionality."""
        query = "explain the use of create Legal disclosure api"
        # Use a higher min_distance threshold to get more results
        results = self.processor.search(query, limit=2, min_distance=1.0)
        self.assertIsInstance(results, list)
        if results:  # If any results found
            self.assertIn('content', results[0])
            self.assertIn('metadata', results[0])
            self.assertIn('distance', results[0])
            # Print detailed results
            print("\nSearch Results for Legal Disclosure API:")
            for i, result in enumerate(results, 1):
                print(f"\nResult {i}:")
                print(f"Distance: {result['distance']}")
                print(f"Content: {result['content'][:300]}...")
                print(f"Headers: {result['metadata']}")
                if result['tables']:
                    print(f"Tables: {len(result['tables'])}")
                if result['json_blocks']:
                    print(f"JSON Blocks: {len(result['json_blocks'])}")
        else:
            print("No results found")

    def test_search_api_capabilities(self):
        """Test search functionality for API capabilities query."""
        query = "What are the limitations and capabilities of the Orders API?"
        results = self.processor.search(query, limit=3)
        self.assertIsInstance(results, list)
        if results:  # If any results found
            self.assertIn('content', results[0])
            self.assertIn('metadata', results[0])
            self.assertIn('distance', results[0])
            print("\nSearch Results for API Capabilities:")
            for i, result in enumerate(results, 1):
                print(f"\nResult {i}:")
                print(f"Distance: {result['distance']}")
                print(f"Content: {result['content'][:200]}...")
                print(f"Headers: {result['metadata']}")
                print(f"Headers: {result['json_blocks']}")
                print(f"Headers: {result['tables']}")

    def setup_database(self):
        try:
            with self.conn.cursor() as cur:
                # Enable vector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Drop existing table if it exists
                cur.execute("DROP TABLE IF EXISTS table_blocks;")
                cur.execute("DROP TABLE IF EXISTS json_blocks;")
                cur.execute("DROP TABLE IF EXISTS document_chunks;")
                
                # Create document_chunks table without title
                cur.execute("""
                    CREATE TABLE document_chunks (
                        id SERIAL PRIMARY KEY,
                        parent_id INTEGER REFERENCES document_chunks(id),
                        content TEXT,
                        embedding vector(1024),
                        metadata JSONB
                    );
                """)
                
                # Create other tables (unchanged)
                cur.execute("""
                    CREATE TABLE json_blocks (
                        id SERIAL PRIMARY KEY,
                        chunk_id INTEGER REFERENCES document_chunks(id),
                        json_content JSONB,
                        metadata JSONB
                    );
                """)
                
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

    @patch('processor.document_processor.HuggingFaceEmbeddings')
    @patch('scraper.scraper.scrape_page')
    @patch('scraper.scraper.get_side_bar_links')
    def test_scrape_and_process_docs(self, mock_get_side_bar_links, mock_scrape_page, mock_embeddings):
        """Test scrape_and_process_docs with mocked sidebar links and page content."""
        try:
            self.processor.scrape_and_process_docs(500)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"scrape_and_process_docs raised an exception: {str(e)}")

if __name__ == '__main__':
    # Create a test loader
    loader = unittest.TestLoader()
    
    # Create a test suite with just the scraper test
    suite = unittest.TestSuite()
    
    # Add the test method we want to run
    # This will properly handle setUp and tearDown
    # test_case = loader.loadTestsFromName(
    #     'test_document_processor.TestDocumentProcessor.test_process_document_with_scraper'
    #     #'test_document_processor.TestDocumentProcessor.test_search'
    # )
    # suite.addTests(test_case)
    
    # Add the new test method
    test_case = loader.loadTestsFromName(
        # 'test_document_processor.TestDocumentProcessor.test_search_api_capabilities'
        'test_document_processor.TestDocumentProcessor.test_scrape_and_process_docs'
    )
    suite.addTests(test_case)
    
    # Run the suite with verbosity=2 to see more details
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
    
    # To run all tests instead, uncomment the following line:
    # unittest.main(verbosity=2) 