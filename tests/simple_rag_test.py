from query_handler import QueryHandler
import logging

# Enable more detailed logging
logging.basicConfig(level=logging.INFO)

def main():
    print("Initializing QueryHandler...")
    handler = QueryHandler()
    
    try:
        # Test with a simple query
        query = "What is Amazon API?"
        print(f"\nQuery: {query}")
        
        # Get response
        response = handler.get_response(
            query=query,
            min_distance=0.9,  # More strict distance
            limit=2  # Fewer results
        )
        
        print("\nResponse from RAG system:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        handler.close()
        print("Resources cleaned up.")

if __name__ == "__main__":
    main() 