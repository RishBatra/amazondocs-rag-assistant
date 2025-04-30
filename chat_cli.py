from query_handler import QueryHandler
import sys
from config import GROQ_CONFIG

SYSTEM_PROMPT = "You are a helpful assistant for Amazon API documentation. Use the provided context to answer as accurately as possible."

def main():
    print("Amazon Docs Chatbot (type 'exit' or 'quit' to end)")
    handler = QueryHandler()
    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    last_user_query = None
    last_search_result = None
    try:
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            # Use LLM to clarify the query if there is a last query/result
            if last_user_query and last_search_result:
                # Prepare a short context string from the last search result
                last_result_context = last_search_result[0]['content'] if last_search_result else ''
                clarification_prompt = (
                    "Rewrite the following user question to be explicit, short, and to the point, using the previous user question and the last search result as context. "
                    "Do not use made-up or unnecessary words. If the question is already explicit, return it unchanged.\n"
                    f"Previous user question: {last_user_query}\n"
                    f"Last search result: {last_result_context}\n"
                    f"Current user question: {user_input}\n"
                    "Rewritten explicit question (short and to the point, no made-up words):"
                )
                try:
                    clarification_response = handler.groq_client.chat.completions.create(
                        model=handler.groq_client.model if hasattr(handler.groq_client, 'model') else "llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": clarification_prompt}],
                        temperature=0.0,
                        max_tokens=128
                    )
                    clarified_query = clarification_response.choices[0].message.content.strip()
                    if clarified_query:
                        search_query = clarified_query
                    else:
                        search_query = user_input
                except Exception as e:
                    search_query = user_input
            else:
                search_query = user_input

            # Get RAG context for the user query
            results = handler.doc_processor.search(
                search_query,
                min_distance=GROQ_CONFIG.get("search_min_distance", 1.0),
                limit=GROQ_CONFIG.get("search_limit", 2)
            )
            if not results:
                context = "I'm sorry, I couldn't find any relevant information in the documentation for your query."
            else:
                context = handler.format_context(results)
            # Add context as a system message (so model can use it)
            conversation.append({"role": "system", "content": f"Context: {context}"})
            # Add user message
            conversation.append({"role": "user", "content": user_input})
            # Call Groq API with full conversation
            try:
                response = handler.groq_client.chat.completions.create(
                    model=handler.groq_client.model if hasattr(handler.groq_client, 'model') else "llama-3.3-70b-versatile",
                    messages=conversation,
                    temperature=GROQ_CONFIG.get("temperature", 0.5),
                    max_tokens=GROQ_CONFIG.get("max_tokens", 8000)
                )
                assistant_reply = response.choices[0].message.content
            except Exception as e:
                assistant_reply = f"[Error from Groq API: {str(e)}]"
            print(f"AI: {assistant_reply}\n")
            # Add assistant reply to conversation
            conversation.append({"role": "assistant", "content": assistant_reply})
            # Update last query and result for next turn
            last_user_query = user_input
            last_search_result = results
    finally:
        handler.close()

if __name__ == "__main__":
    main() 