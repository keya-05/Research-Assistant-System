from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel
from dotenv import load_dotenv
import os

load_dotenv()

def get_llm(temperature: float = 0.2) -> BaseChatModel:
    # Primary Model: Google Gemini
    primary_llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        temperature=temperature,
        max_retries=3,
        timeout=60
    )
    
    # Fallback Model: Groq (Llama 3.3 70B)
    # Fast, high rate limits, and highly capable
    fallback_llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        max_retries=3,
        timeout=60
    )
    
    # Return the resilient LLM chain
    return primary_llm.with_fallbacks([fallback_llm])