from processor.document_processor import DocumentProcessor
from db.init_db import init_database
from config import DB_CONFIG
from scraper.scraper import get_side_bar_links, scrape_page
import logging
import time

def main():
    # Initialize logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Database configuration
    db_config = {
        'host': DB_CONFIG['host'],
        'dbname': DB_CONFIG['dbname'],
        'user': DB_CONFIG['user'],
        'password': DB_CONFIG['password']
    }
    
    # Initialize database
    print("Initializing database...")
    init_database(db_config)
    
    # Initialize processor
    print("Initializing document processor...")
    processor = DocumentProcessor(db_config)
    
    try:
        # Get URLs
        urls = get_side_bar_links()
        logger.info(f"Found {len(urls)} URLs to process")
        
        for url in urls:
            try:
                logger.info(f"Processing URL: {url}")
                
                # Scrape content
                content = scrape_page(url)
                if not content:
                    logger.warning(f"No content found for {url}")
                    continue
                
                logger.debug(f"Content length: {len(content)}")
                
                # Process document
                processor.process_document(
                    content=content,
                    metadata={
                        'source': url,
                        'type': 'api_documentation',
                        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                )
                
                logger.info(f"Successfully processed {url}")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}", exc_info=True)
                continue
                
    except Exception as e:
        logger.error(f"Main process error: {str(e)}", exc_info=True)
    finally:
        processor.close()

if __name__ == "__main__":
    main() 