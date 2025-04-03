from scraper.scraper import get_side_bar_links, scrape_page
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from config import EMBEDDING_MODEL_CONFIG, TEXT_SPLITTER_CONFIG
import time

def process_docs():
    #1.get all documentation URLs
    urls = get_side_bar_links()

    #2. scrape and clean content
    documents = []
    for url in urls:
        content = scrape_page(url)
        if content:
            documents.append({
                "text": content,
                "metadata": {"source": url}
            })
        #rate limiting - pausing for 1 second between each request
        time.sleep(1)
    
    #Chunk documents
    chunks = chunk_documents(documents)
    #create vector store
    create_vector_store(chunks)

def create_vector_store(chunks):
    #embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_CONFIG["model_name"],
        model_kwargs={"device": EMBEDDING_MODEL_CONFIG["device"]}
    )
    #create vector store
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local("faiss_index")

def chunk_documents(documents):
    if(TEXT_SPLITTER_CONFIG["splitter_type"] == "MarkdownHeaderTextSplitter"):
        text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ],
            strip_headers = False
        )
    split_docs = text_splitter.split_text(documents)
    print("split_docs below")
    split_docs
    return split_docs
    # else:
    #     text_splitter = RecursiveCharacterTextSplitter(
    #         chunk_size=TEXT_SPLITTER_CONFIG["chunk_size"],
    #         chunk_overlap=TEXT_SPLITTER_CONFIG["chunk_overlap"],
    #         separators=TEXT_SPLITTER_CONFIG["separators"],
    #         keep_separator=TEXT_SPLITTER_CONFIG["keep_separator"],
    #         strip_whitespace=TEXT_SPLITTER_CONFIG["strip_whitespace"]
    #     )
    #     return text_splitter.split_documents(documents)
    


