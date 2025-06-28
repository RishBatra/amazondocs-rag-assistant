import os
import glob
import re
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

def extract_xml(text: str, tag: str) -> str:
    """
    Extracts the content of the specified XML tag from the given text. Used for parsing structured responses 

    Args:
        text (str): The text containing the XML.
        tag (str): The XML tag to extract content from.

    Returns:
        str: The content of the specified XML tag, or an empty string if the tag is not found.
    """
    match = re.search(f'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
    return match.group(1) if match else ""

if __name__ == "__main__":
    cleanup_amazon_docs()
