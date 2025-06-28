from typing import List, Dict, Any
from transformers import AutoTokenizer, AutoModel
import torch
from processor.document_processor import DocumentProcessor
from config import DB_CONFIG, EMBEDDING_MODEL_CONFIG, GROQ_CONFIG, SEARCH_MODE, SYSTEM_PROMPT, NO_RESULTS_MESSAGE, FALLBACK_CONTEXT_MESSAGE, QUERY_WRITER_PROMPT, EVALUATOR_PROMPT
import logging
import os
from groq import Groq
from scraper.utils import extract_xml

class QueryHandler:
    def __init__(self):
        """Initialize the query handler with document processor and model"""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize document processor
        self.doc_processor = DocumentProcessor(DB_CONFIG)
        
        # Initialize model and tokenizer for embeddings
        self.model_name = EMBEDDING_MODEL_CONFIG["model_name"]
        self.device = EMBEDDING_MODEL_CONFIG["device"]
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
        
        # Initialize Groq client for text generation
        try:
            self.groq_client = Groq(api_key=GROQ_CONFIG["api_key"])
            self.logger.info("Groq client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Groq client: {str(e)}")
            self.groq_client = None
        
    def format_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Format search results into a context string"""
        context = []
        
        for result in search_results:
            # Add main content
            context.append(f"Content: {result['content']}\n")
            
            # Add JSON blocks if any
            if result['json_blocks']:
                context.append("JSON Examples:")
                for json_block in result['json_blocks']:
                    context.append(f"{str(json_block)}\n")
                    context.append(f"Metadata: {json_block['metadata']}\n")
            
            # Add tables if any
            if result['tables']:
                context.append("Table Information:")
                for table in result['tables']:
                    headers = table['headers']
                    content = table['content']
                    metadata = table['metadata']
                    context.append(f"Headers: {headers}")
                    context.append(f"Content: {content}\n")
                    context.append(f"Metadata: {metadata}\n")
            
            context.append("-" * 50 + "\n")  # Separator between different results
            
        return "\n".join(context)
    
    def generate_prompt(self, query: str, context: str) -> str:
        """Generate a prompt combining the query and context"""
        return f"""Based on the following Amazon API documentation:

        {context}

        Question: {query}

        Answer: Let me help you with that."""
    
    def query_writer(self, search_results, query, previous_attempts: str = "") -> tuple[str,str]:
        """This method rewrites the user query and incorporates the feedback from evaluator.
        Args:
        search_results: The results received from vector search using the given query
        query: The query used for searching
        context: Previous attempts and its feedback 
        """

        full_prompt = f"""{QUERY_WRITER_PROMPT}
        <originalUserQuery>
        {query}
        </originalUserQuery>

        <search>

        {previous_attempts} """ if previous_attempts else f"""
        
        """
        


        
        

    def query_evaluator(self, search_results, query) -> tuple[str, str]:
        """This method cheks the search results for relevance.
        If the results are not relevant it gives feedback to mdoify the query.

        Args:
        search_results: The results received from vector search using the given query
        query: The query used for searching
        """
        full_prompt = EVALUATOR_PROMPT + f"""
        <searchResults>
        {search_results}
        </searchResults>

        <query>
        {query}
        </query>
        """
        response = self.call_llm(full_prompt)
        evaluation = extract_xml(response, "evaluation")
        feedback = extract_xml(response, "feedback")
        self.logger("=== EVALUATION START ===")
        self.logger(f"Status {evaluation}")
        self.logger(f"Feedback {feedback}")
        self.logger("=== EVALUATION END ===")

        return evaluation, feedback
    
    def loop(self, query: str, search_results: str) -> tuple[str, list[dict]]:
        memory = []
        chain_of_thought = []

        thoughts, generated_query = self.query_writer(search_results, query)





    def call_llm(self, prompt: str, system_prompt: str = "", model = GROQ_CONFIG["model"]) -> str:
        """
        Calls the model with the given prompt and returns th response.

        Args:
        prompt (str): The user prompt.
        system_prompt
        """
        if self.groq_client:
                try:
                    # Call Groq API
                    response = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=GROQ_CONFIG["temperature"],
                        max_tokens=GROQ_CONFIG["max_tokens"]
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    self.logger.error(f"Error using Groq API: {str(e)}")
                    # Fall back to using context directly if Groq fails
                    return FALLBACK_CONTEXT_MESSAGE


    def get_search_results(self, query, min_distance, limit) -> str:
        
        # Get relevant documents based on SEARCH_MODE
            if SEARCH_MODE == "hybrid":
                search_results = self.doc_processor.hybrid_search(
                    query=query,
                    min_distance=min_distance,
                    limit=limit
                )
            elif SEARCH_MODE == "keyword":
                search_results = self.doc_processor.keyword_search(
                    query=query,
                    limit=limit
                )
            else:  # Default to semantic
                search_results = self.doc_processor.search(
                    query=query,
                    min_distance=min_distance,
                    limit=limit
                )
            
            if not search_results:
                return NO_RESULTS_MESSAGE
            else:
                return search_results
            



    def get_response(self, query: str, min_distance: float = 0.8, limit: int = 1) -> str:
        """Get response for a query using RAG approach"""
        try:
            # Get relevant documents based on SEARCH_MODE
            search_results = self.get_search_results(query , min_distance, limit)
            
            # Format context from search results
            context = self.format_context(search_results)
            
            # Generate prompt
            prompt = self.generate_prompt(query, context)
            
            # Use Groq for text generation
            if self.groq_client:
                try:
                    # Call Groq API
                    response = self.groq_client.chat.completions.create(
                        model=GROQ_CONFIG["model"],
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=GROQ_CONFIG["temperature"],
                        max_tokens=GROQ_CONFIG["max_tokens"]
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    self.logger.error(f"Error using Groq API: {str(e)}")
                    # Fall back to using context directly if Groq fails
                    return FALLBACK_CONTEXT_MESSAGE.format(context=context)
            # else:
            #     # Fallback to old method if Groq client not available
            #     inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(self.device)
                
            #     with torch.no_grad():
            #         outputs = self.model(**inputs)
            #         # Get the model's output logits and convert to text
            #         logits = outputs.logits if hasattr(outputs, 'logits') else outputs.last_hidden_state
            #         predicted_tokens = torch.argmax(logits, dim=-1)
            #         model_response = self.tokenizer.decode(predicted_tokens[0], skip_special_tokens=True)
                
            #     return model_response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            return f"An error occurred while processing your query: {str(e)}"
        
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'doc_processor'):
            self.doc_processor.close()

# Example usage
if __name__ == "__main__":
    handler = QueryHandler()
    try:
        user_query = input("Enter your query: ")
        response = handler.get_response(user_query)
        print(f"Query: {user_query}\n")
        print(f"Response: {response}")
    finally:
        handler.close() 