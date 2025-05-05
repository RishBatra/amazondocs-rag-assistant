from groq import Groq
import os

# The API key is already in your config.py
from config import GROQ_CONFIG
api_key = GROQ_CONFIG["api_key"]

# Initialize the Groq client
client = Groq(api_key=api_key)

# Test a simple prompt
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for Amazon API documentation."},
            {"role": "user", "content": "What is RAG?"}
        ],
        temperature=0.5,
        max_tokens=100
    )
    
    print("Groq API test successful!")
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"Error using Groq API: {str(e)}") 