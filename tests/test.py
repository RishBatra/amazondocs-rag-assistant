import sys
sys.path.append('..')  # Add parent directory to Python path
from typing import List, Dict, Any
from scraper.scraper import get_side_bar_links, scrape_page
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from processor.processor import chunk_documents
from config import TEXT_SPLITTER_CONFIG, FILE_PATHS
from transformers import AutoTokenizer
import torch
import os
import json
import re

def test_cuda():
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"Current device: {torch.cuda.get_device_name(0)}")

def test_scrape_first_five():
    # Get sidebar links
    links = get_side_bar_links()
    
    # Take first 5 links
    test_links = links[:5]
    
    # Scrape each link and write to separate files
    for i, link in enumerate(test_links):
        content = scrape_page(link)
        if content:
            filename = FILE_PATHS["test_data"]["summaries"].format(i+1)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Content written to {filename}")
        else:
            print(f"Could not extract content from {link}")
                
    print("Content from first 5 links written to separate files")
    return True

def test_sidebar_links():
    # Get sidebar links
    links = get_side_bar_links()
        
    # Write first few links to a test file
    with open(FILE_PATHS["test_data"]["test_links"], 'w') as f:
        # Write first 5 links as a sample
        for i, link in enumerate(links[:5]):
            f.write(f"{i+1}. {link}\n")
        
    print(f"Total links found: {len(links)}")
    print("First 5 links written to test_links.txt")
    return len(links) > 0

def visual_chunk_test(sample_text, splitter_config):
    """Test chunking visually - simple output of first 5 chunks"""
    # Create document and split into chunks
    #doc = Document(page_content=sample_text, metadata={"source": "test_doc"})
    chunks = chunk_documents(sample_text)
    
    print(f"\nTotal chunks: {len(chunks)}\n")
    
    # Only show first 5 chunks
    for i, chunk in enumerate(chunks[:5]):
        print(f"\nCHUNK {i+1}:")
        # content = chunk.page_content
        # tokenizer = AutoTokenizer.from_pretrained("HuggingFaceH4/zephyr-7b-beta")
        # tokens = tokenizer.encode(content, return_tensors="pt")
        # token_count = tokens.shape[1]  # Get token count
        # print(f"Token count: {token_count}")
        # print(content)
        # print("-" * 40)  # Simple separator between chunks

def test_json_extraction():
    """Test JSON block extraction from markdown"""
    from processor.document_processor import DocumentProcessor
    
    # Initialize DocumentProcessor with minimal config
    # processor = DocumentProcessor({'host': 'dummy'})
    
    # Read sample doc
    with open(FILE_PATHS["test_data"]["sample_doc"], 'r', encoding='utf-8') as f:
        sample_doc = f.read()
    
    # Extract JSON blocks
    json_blocks = extract_json_blocks(sample_doc)
    
    print(f"\nFound {len(json_blocks)} JSON blocks")
    # Write all JSON blocks to file
    with open('json_extraction_results.txt', 'w') as f:
        json.dump(json_blocks, f, indent=2)
    
    print("JSON blocks written to json_extraction_results.txt")
    return len(json_blocks) > 0


def extract_tables(text: str) -> List[Dict[str, Any]]:
    """Extract markdown tables from text"""
    tables = []
    
    # Single pattern to catch all table formats
    table_pattern = r"\|[^\n]+\|\n\|[-:\| ]+\|\n(?:\|?[^\n]+\|\n)+"
    
    for match in re.finditer(table_pattern, text):
        table_text = match.group(0)
        table = process_table(table_text)
        if table:
            tables.append(table)
    
    return sorted(tables, key=lambda x: x['position'])

def process_table(table_text: str) -> Dict[str, Any]:
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

def test_table_extraction():
    # Read sample doc
    with open(FILE_PATHS["test_data"]["sample_doc"], 'r', encoding='utf-8') as f:
        sample_doc = f.read()
    
    # Extract tables
    tables = extract_tables(sample_doc)
    
    # Write tables to output file
    output_file = "table_extraction_results.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Found {len(tables)} tables\n\n")
        
        for i, table in enumerate(tables):
            f.write(f"{'='*80}\n")
            f.write(f"TABLE {i+1}:\n")
            f.write(f"{'='*80}\n")
            f.write(f"Headers: {table['headers']}\n")
            f.write("\nRaw table:\n")
            f.write(table['raw_text'])
            f.write(f"\n\nNumber of rows: {len(table['content'])}\n")
            f.write("\nRows:\n")
            for row_num, row in enumerate(table['content'], 1):
                f.write(f"\nRow {row_num}:\n")
                f.write(json.dumps(row, indent=2))
                f.write("\n")
            f.write(f"\n{'='*80}\n\n")
    
    print(f"Table extraction results written to {output_file}")
    return len(tables) > 0

def extract_json_blocks(text: str) -> List[Dict[str, Any]]:
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

def test_database_connection():
    """Test database connection and operations"""
    from processor.document_processor import DocumentProcessor
    from config import DB_CONFIG
    
    processor = DocumentProcessor(DB_CONFIG)
    
    # First set up the schema
    if not processor.setup_database():
        processor.close()
        return False
        
    # Then test with correct dimensions
    try:
        with processor.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO document_chunks (parent_id, title, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                'test_title',
                'test_content',
                [0.1] * 1024,  # Match BAAI model dimensions
                'test_metadata'
            ))
            
            result = cur.fetchone()
            processor.logger.debug(f"Test insert result: {result}")
            
            processor.conn.rollback()
            return True
            
    except Exception as e:
        processor.logger.error(f"Database test failed: {str(e)}", exc_info=True)
        return False
    finally:
        processor.close()

def test_setup_database():
    """Test only database setup"""
    from processor.document_processor import DocumentProcessor
    from config import DB_CONFIG
    
    processor = DocumentProcessor(DB_CONFIG)
    success = processor.setup_database()
    processor.close()
    print(f"Database setup {'succeeded' if success else 'failed'}")
    return success

# Update main to include new tests
if __name__ == "__main__":
    import json  # Add this import at the top of the file
    # print("Testing database connection...")
    # success = test_database_connection()
    # print(f"Database connection test {'passed' if success else 'failed'}")
    
    # test_setup_database()

    # print("Testing JSON extraction...")
    # json_result = test_json_extraction()
    # print(f"JSON extraction test {'passed' if json_result else 'failed'}")
    
    # print("\nTesting table extraction...")
    # table_result = test_table_extraction()
    # print(f"Table extraction test {'passed' if table_result else 'failed'}")
    
    # Original chunk test
    # print("\nTesting chunking...")
    # with open(FILE_PATHS["test_data"]["sample_doc"], 'r', encoding='utf-8') as f:
    #     sample_doc = f.read()
    # visual_chunk_test(sample_doc, TEXT_SPLITTER_CONFIG)

# if __name__ == "__main__":
#     #test_sidebar_links()
#     test_scrape_first_five()
#     #test_cuda()
