import os
import glob

def cleanup_amazon_docs():
    """
    Deletes all amazon_docs_summary_*.txt files in the current directory
    """
    # Find all files matching pattern
    files = glob.glob("amazon_docs_summary_*.txt")
    
    # Delete each file
    for file in files:
        try:
            os.remove(file)
            print(f"Deleted {file}")
        except OSError as e:
            print(f"Error deleting {file}: {e}")

if __name__ == "__main__":
    cleanup_amazon_docs()
